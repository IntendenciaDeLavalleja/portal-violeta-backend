from flask_mail import Message
from flask import current_app, render_template
from app.extensions import mail
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error al enviar correo electrónico: {e}")


def send_email(subject, recipients, text_body, html_body, attachments=None):
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    if attachments:
        for att in attachments:
            msg.attach(att['filename'], att['content_type'], att['data'])

    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg),
    ).start()


def send_2fa_email(to_email, code):
    subject = "[Punto Violeta Digital] Código de verificación de acceso"

    html_body = render_template('emails/2fa_code.html', code=code)

    send_email(
        subject=subject,
        recipients=[to_email],
        text_body=f"Tu código de verificación para el panel de administración del Punto Violeta: {code}. Expira en 10 minutos.",
        html_body=html_body,
    )


def send_contact_confirmation_email(to_email: str, msg):
    """Envía un email de confirmación a quien completó el formulario de contacto."""
    subject = "Tu mensaje fue recibido - Punto Violeta"

    html_body = render_template('emails/contact_confirmation.html', msg=msg)

    send_email(
        subject=subject,
        recipients=[to_email],
        text_body=(
            "Gracias por escribirnos. Tu mensaje fue recibido y "
            "nos comunicaremos contigo en el horario que indicaste. "
            "Si es una emergencia, por favor comunicate al 911 o al servicio de emergencias local."
        ),
        html_body=html_body,
    )
