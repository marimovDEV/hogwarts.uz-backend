
# ============= CMS SERIALIZERS =============

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ['id', 'name', 'profession', 'text_uz', 'text_ru', 'image', 'rating', 'is_active', 'is_highlighted', 'created_at']

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'subtitle', 'image', 'mobile_image', 'button_text', 'button_link', 'order', 'is_active', 'created_at']
