import jwt
import logging
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

logger = logging.getLogger(__name__)

def generate_token(user):
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(days=settings.JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired: {token[:20]}...")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


class JWTAuthentication(BaseAuthentication):
    """Custom JWT Authentication with detailed logging for debugging 403s"""
    
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        try:
            parts = auth_header.split()
            if len(parts) != 2:
                logger.warning(f"Invalid Authorization header format: {auth_header}")
                return None
                
            prefix, token = parts
            if prefix.lower() != 'bearer':
                logger.warning(f"Invalid Authorization prefix: {prefix}")
                return None
        except Exception as e:
            logger.error(f"Error parsing Authorization header: {e}")
            return None
        
        payload = decode_token(token)
        if not payload:
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            logger.warning(f"User not found for token payload: {payload}")
            return None
        except KeyError:
            logger.error(f"Token payload missing user_id: {payload}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user: {e}")
            return None
        
        return (user, token)
