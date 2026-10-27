from insurance_operations.application import create_app
from insurance_operations.database.connection import create_database_engine
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.ingress import configure_twilio_ingress
from insurance_operations.telephony.settings import TelephonyProviderSettings
from insurance_operations.whatsapp.routes import configure_whatsapp
from insurance_operations.whatsapp.settings import WhatsAppSettings

settings = ApiSettings()
database_engine = create_database_engine(
    settings,
    service_name="api",
)
app = create_app(settings, database_engine)

telephony_provider_settings = TelephonyProviderSettings()
configure_twilio_ingress(
    app,
    telephony_provider_settings,
    database_engine,
)
configure_whatsapp(app, settings, WhatsAppSettings(), database_engine)
