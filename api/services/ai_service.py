import logging
import random
from django.utils import timezone
from ..models import AIAssistantFAQ, AIConversation, AIMessage, AIUnansweredQuestion
from django.db.models import Q

logger = logging.getLogger(__name__)

class AIService:
    """
    Hybrid AI Engine: FAQ Matching + LLM Fallback
    """

    @staticmethod
    def get_or_create_conversation(user=None, session_id=None, context_url=None):
        if user and user.is_authenticated:
            conv, created = AIConversation.objects.get_or_create(
                user=user,
                defaults={'context_url': context_url}
            )
        else:
            conv, created = AIConversation.objects.get_or_create(
                session_id=session_id,
                defaults={'context_url': context_url}
            )
        
        if not created and context_url:
            conv.context_url = context_url
            conv.save(update_fields=['context_url', 'last_active'])
        
        return conv

    @staticmethod
    def process_query(conversation, question, language='uz'):
        """
        Main logic for processing user query
        1. Find best FAQ match
        2. If no match, use LLM (Fallback)
        3. Log both query and response
        """
        # Log user message
        AIMessage.objects.create(
            conversation=conversation,
            role='user',
            content=question
        )

        # 1. Try to find match in FAQ
        faq_match = AIService.find_faq_match(question, language)
        
        if faq_match:
            answer = faq_match.answer_uz if language == 'uz' else faq_match.answer_ru
            action = {
                'label': (faq_match.action_label_uz if language == 'uz' else faq_match.action_label_ru) or "Batafsil",
                'link': faq_match.action_link
            } if faq_match.action_link else None

            # Log bot response
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=answer,
                source='FAQ',
                faq=faq_match
            )
            
            return {
                'type': 'FAQ',
                'content': answer,
                'action': action,
                'faq_id': faq_match.id
            }

        # 2. Fallback to LLM (Mocked for now, easily pluggable)
        llm_response = AIService.call_llm(question, conversation.context_url, language)
        
        # Log bot response
        msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=llm_response,
            source='LLM'
        )

        # Log as unanswered for admin review
        AIUnansweredQuestion.objects.create(
            question=question,
            user=conversation.user,
            context_url=conversation.context_url
        )

        return {
            'type': 'LLM',
            'content': llm_response,
            'message_id': msg.id
        }

    @staticmethod
    def find_faq_match(question, language):
        """
        Simple keyword based matching. Can be improved with trigram search or vector embeddings.
        """
        question = question.lower().strip()
        words = question.split()
        
        # Priority 1: Exact matches or very close matches in search_tags
        faqs = AIAssistantFAQ.objects.filter(is_active=True)
        
        for faq in faqs:
            tags = [t.strip().lower() for t in faq.search_tags.split(',')] if faq.search_tags else []
            # Check if all words or major words are in tags
            if any(word in tags for word in words):
                return faq
            
            # Simple substring match in questions
            q_text = faq.question_uz.lower() if language == 'uz' else faq.question_ru.lower()
            if question in q_text or q_text in question:
                return faq

        return None

    @staticmethod
    def call_llm(question, context_url, language='uz'):
        """
        Fallback LLM Logic. 
        In production, call OpenAI/DeepSeek API here.
        """
        # Context Awareness logic
        context_hint = ""
        if context_url:
            if 'course' in context_url:
                context_hint = "Foydalanuvchi hozirda kurslar bo'limida. " if language == 'uz' else "Пользователь сейчас в разделе курсов. "
            elif 'olympiads' in context_url:
                context_hint = "Foydalanuvchi hozirda olimpiadalar bo'limida. " if language == 'uz' else "Пользователь сейчас в разделе олимпиad. "

        # Mock responses based on language
        if language == 'uz':
            responses = [
                f"{context_hint}Hozircha o'rganish jarayonidaman, lekin sizga yordam berishga harakat qilaman. Savolingizni operatorimizga yo'naltirishim mumkin.",
                f"{context_hint}Kechirasiz, bunga aniq javob topa olmadim. Hogwords platformasi haqida savollaringiz bo'lsa, yordam berishim mumkin.",
            ]
        else:
            responses = [
                f"{context_hint}Я пока учусь, но постараюсь вам помочь. Могу перенаправить ваш вопрос оператору.",
                f"{context_hint}Извините, я не нашел точного ответа. Если у вас есть вопросы о платформе Hogwords, я готов помочь.",
            ]
            
        return random.choice(responses)

    @staticmethod
    def rate_response(message_id, rating, feedback=None):
        try:
            msg = AIMessage.objects.get(id=message_id)
            msg.rating = rating
            if feedback:
                msg.feedback = feedback
            msg.save()
            
            # If rejected, maybe flag for admin review
            if rating == -1:
                AIUnansweredQuestion.objects.create(
                    question=f"LOW RATING for: {msg.content} | Original query: {msg.conversation.messages.filter(role='user').last().content}",
                    user=msg.conversation.user,
                    context_url=msg.conversation.context_url
                )
            
            return True
        except AIMessage.DoesNotExist:
            return False
