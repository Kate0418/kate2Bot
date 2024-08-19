FROM python:3.8
WORKDIR /kate2Bot
RUN pip install discord.py
RUN pip install PyNaCl
RUN pip install openai
RUN pip install pytz
RUN pip install python-dotenv
COPY . .
CMD ["python3", "kate2Bot.py"]