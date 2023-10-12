import yagmail


def send_email(user, password, to, subject, text):
    print(user)
    print(password)
    yag = yagmail.SMTP(user, password)

    # Send email
    yag.send(
        to=to,
        subject=subject,
        contents=text,
    )


def format_messages(messages):
    messages_string = ""
    for message in messages:
        messages_string += f"{message['role']}: {message['content']}\n"

    return messages_string
