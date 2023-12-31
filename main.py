# Importing libraries
import os
from typing import Any
import dotenv
import imaplib
import email

dotenv.load_dotenv()


class Email:
    def __init__(self, imap_url="imap.gmail.com"):
        # this is done to make SSL connection with GMAIL
        con = imaplib.IMAP4_SSL(imap_url)

        # logging the user in
        con.login(os.getenv("EMAIL_USER", ""), os.getenv("EMAIL_PASSWORD", ""))

        # calling function to check for email under this label
        con.select("Inbox")
        self.con = con

    def run(self):
        # fetching emails from this user "tu**h*****1@gmail.com"
        msgs = self.get_emails(self.search("FROM", "info@noreply.tngdigital.com.my"))
        # Uncomment this to see what actually comes as data
        # print(msgs)

        # Finding the required content from our msgs
        # User can make custom changes in this part to
        # fetch the required content he / she needs

        # printing them by the order they are displayed in your gmail
        for msg in msgs[::-1]:
            for sent in msg:
                if type(sent) is tuple:
                    # encoding set as utf-8
                    content = str(sent[1], "utf-8")
                    data = str(content)

                    # Handling errors related to unicodenecode
                    try:
                        indexstart = data.find("ltr")
                        data2 = data[indexstart + 5 : len(data)]
                        indexend = data2.find("</div>")

                        # printing the required content which we need
                        # to extract from our email i.e our body
                        print(data2[0:indexend])

                    except UnicodeEncodeError as e:
                        pass

    # Function to get email content part i.e its body part
    def get_body(self, msg):
        if msg.is_multipart():
            return self.get_body(msg.get_payload(0))
        else:
            return msg.get_payload(None, True)

    # Function to search for a key value pair
    def search(self, key, value):
        result, data = self.con.search(None, key, '"{}"'.format(value))
        return data

    # Function to get the list of emails under this label
    def get_emails(self, result_bytes):
        msgs = []  # all the email data are pushed inside an array
        for num in result_bytes[0].split():
            typ, data = self.con.fetch(num, "(RFC822)")
            msgs.append(data)
        return msgs


def main():
    em = Email()
    em.run()


if __name__ == "__main__":
    main()
