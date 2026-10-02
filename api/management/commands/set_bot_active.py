from api.models_settings import PlatformSettings, PaymentProviderConfig

# 1. Update Platform Settings
settings, created = PlatformSettings.objects.get_or_create(id=1)
settings.active_payment_type = 'BOT'
settings.save()

print(f"✅ Platform Active Payment Type set to: {settings.active_payment_type}")

# 2. Ensure Bot Provider Config exists (though logic uses BotConfig mostly)
# We need this if PaymentModal uses PaymentProviderConfig to find 'BOT' specific details.
bot_provider, created = PaymentProviderConfig.objects.get_or_create(
    type='BOT',
    provider='USERBOT',
    defaults={'name': 'Telegram Bot Payment', 'is_active': True}
)
if not bot_provider.is_active:
    bot_provider.is_active = True
    bot_provider.save()

print("✅ Bot Payment Provider ensured.")
