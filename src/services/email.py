from fastapi_mail import FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors

from pydantic import EmailStr

from src.services.auth import auth_serviсe

from src.conf.config import conf


async def send_email(email: EmailStr, username: str, host: str):
    """
    Get a list of contacts.

    Parameters:
    - limit (int): The maximum number of contacts to retrieve. Default is 10, minimum is 1, and maximum is 500.
    - offset (int): The index of the first contact to retrieve. Default is 0.
    - db (AsyncSession): The database session to use for the operation.
    - user (User): The authenticated user making the request.

    Returns:
    - list[ContactResponseSchema]: A list of ContactResponseSchema objects representing the contacts.
    """
    try:
        token_verification = auth_serviсe.create_email_token({"sub": email})
        message = MessageSchema(
            subject="Confirm your email ",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="email_verification.html")
    except ConnectionErrors as err:
        print(err)


async def send_password_reset_email(email: EmailStr, username: str, host: str):
    """
    Sends a password reset email to the specified user.

    Parameters:
    - email (EmailStr): The email address of the user to send the password reset email to.
    - username (str): The username of the user to send the password reset email to.
    - host (str): The hostname of the website or application.

    Returns:
    - None: This function does not return any value. It sends an email asynchronously.

    Raises:
    - ConnectionErrors: If there is an error connecting to the email service.
    """
    try:
        token_verification = auth_serviсe.create_email_token({"sub": email})
        message = MessageSchema(
            subject="Password reset ",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="password_reset_mail.html")
    except ConnectionErrors as err:
        print(err)
