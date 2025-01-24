import os
import openai
import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters.command import Command
from aiogram.filters import Text
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from token_ import OPENAI_TOKEN, TG_TOKEN
from db_config_ import HOST, DATABASE, USER, PASSWORD
import psycopg2
import psycopg2.extras as extras
from langchain import OpenAI, LLMChain
from langchain.llms import OpenAIChat
from langchain.prompts.prompt import PromptTemplate
from parser_rss import ParserRSS
import traceback
from dateutil.parser import parse
import random as rand



conn = psycopg2.connect(
    host=HOST,
    database=DATABASE,
    user=USER,
    password=PASSWORD,
    sslmode="disable")

SETTINGS = {'Bot_status': 'stop'}
CHANEL_RU = '-1001784688405'
CHANEL_EN = '-1001289683117'
ADMINISTRATORS = ['733075616']

SHOW_ERROR_TEXT = True

router = Router()

os.environ['OPENAI_API_KEY'] = OPENAI_TOKEN # OpenAI key

parserRSS = ParserRSS('https://finance.yahoo.com/news/rss')

def is_admin_check(bot_rout):
    async def check_bot_status(*args, **kwargs):
        chat_id = str(args[0].chat.id)
        if chat_id in ADMINISTRATORS:
            return await bot_rout(args[0])
        else:
            return await args[0].answer('You are not allowed to use this bot.')
    return check_bot_status


@router.message(Command("start"))
@is_admin_check
async def send_welcome(message: types.Message):
    try:
        chat_id = message.chat.id
        await message.answer('Bot is ready')
    except Exception as e:
        print(traceback.format_exc())
        if SHOW_ERROR_TEXT:
            await message.answer(str(e)+'\nPlease, try again')
        else:
            await message.answer('Please, try again')

def get_links_for_last_3_days():
    query = "select link from article where datetime > now() - INTERVAL '2 days'"
    cursor = conn.cursor()
    rows = cursor.execute(query)
    cursor.close
    if rows is None:
        return []
    else:
        return rows
    
    
def get_gpt_text_en(text):
    TEMPLATE = """Act like Scrooge McDuck. You are the richest drake in the world and you decided to open your telegram channel to share your wisdom and thoughts with other people. Now you are better known by the name Scrooge McQuack, which you use always and everywhere. The text of the news will be written below, which you will retell and comment on in your own style, with jokes and irony. Try to make the text as expressive and interesting as possible for readers. Since all your subscribers already know that you are Scrooge McQuack, do not say hello and do not introduce yourself at the beginning. Your story about the news should be short, limit it to 350 words.
    \"\"\"News\"\"\"
    {text}
    \"\"\"News\"\"\"
"""
    prompt = PromptTemplate(template=TEMPLATE, input_variables=["text"])
    llm_chain = LLMChain(llm=OpenAIChat(model_kwargs={'temperature':0.7, 'max_tokens':-1}, model_name="gpt-3.5-turbo"), prompt=prompt)
    llm_inputs = {
                "text": text
                }
    result = llm_chain.predict(**llm_inputs)
    return result.strip()
    

def get_gpt_text_ru(text):
    TEMPLATE = """Translate this to Russian. Translate 'Scrooge McQuack' as 'Скрудж МакКряк'. Translate 'richest drake in the world' as 'богатейший селезень в мире'. Translate 'always keep your eyes on the prize' as 'не сводите глаз с цели'.
    {text}
"""
    prompt = PromptTemplate(template=TEMPLATE, input_variables=["text"])
    llm_chain = LLMChain(llm=OpenAIChat(model_kwargs={'temperature':0.9, 'max_tokens':-1}, model_name="gpt-3.5-turbo"), prompt=prompt)
    llm_inputs = {
                "text": text
                }
    result = llm_chain.predict(**llm_inputs)
    return result.strip()
    
def get_gpt_title_ru(text):
    TEMPLATE = """Translate this to Russian.
    {text}
"""
    prompt = PromptTemplate(template=TEMPLATE, input_variables=["text"])
    llm_chain = LLMChain(llm=OpenAIChat(model_kwargs={'temperature':0.9, 'max_tokens':-1}, model_name="gpt-3.5-turbo"), prompt=prompt)
    llm_inputs = {
                "text": text
                }
    result = llm_chain.predict(**llm_inputs)
    return result.strip()   


async def make_posts(article, chanel_en, chanel_ru):
    print(article['title'], ': ', article['link'])
    text = ''
    text_en = get_gpt_text_en(article['title'] + '\n\n' + article['text'])
    text_ru = get_gpt_text_ru(text_en)
    title_en = article['title']
    title_ru = get_gpt_title_ru(title_en)
    post_en = f"<b>{title_en}</b>\n\n" + text_en
    post_ru = f"<b>{title_ru}</b>\n\n" + text_ru
    await bot.send_message(chanel_en, post_en[:4095], parse_mode='HTML')
    await bot.send_message(chanel_ru, post_ru[:4095], parse_mode='HTML')


def update_posted_table(article):
    query = "INSERT INTO article(link, title, text, datetime) VALUES (%s, %s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(query, (article['link'], article['title'],
                               article['text'], article['datetime']))
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        print(traceback.format_exc())
        conn.rollback()
        cursor.close()
    cursor.close()

        
@router.message(Command("stop_posting"))
@is_admin_check
async def stop_posting(message: types.Message):
    chat_id = message.chat.id
    SETTINGS['Bot_status'] = 'stop'
    await message.answer("Posting has been stoped")

    
@router.message(Command("start_posting"))
@is_admin_check
async def start_posting(message: types.Message):
    try:
        chat_id = message.chat.id
        await message.answer("Posting has been started")
        SETTINGS['Bot_status'] = 'work'
        posted = get_links_for_last_3_days()
        while SETTINGS['Bot_status'] == 'work':
            try:
                articles = parserRSS.get_articles(parse('05.08.2023'))
                articles = [a for a in articles if a['link'] not in posted]
                for article in articles:
                    try:
                        await make_posts(article, CHANEL_EN, CHANEL_RU)
                        posted.append(article['link'])
                        update_posted_table(article)
                        await asyncio.sleep(60 + rand.randrange(1, 300, 15))
                    except Exception as e:
                        print(traceback.format_exc())
                        await asyncio.sleep(10)
                await asyncio.sleep(120)
            except Exception as e:
                print(traceback.format_exc())
                await asyncio.sleep(10)
    except Exception as e:
        print(traceback.format_exc())
        if SHOW_ERROR_TEXT:
            await message.answer(str(e)+'\nError')
        else:
            await message.answer('Error')

bot = Bot(token=TG_TOKEN)

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)
    


if __name__ == "__main__":
    asyncio.run(main())
