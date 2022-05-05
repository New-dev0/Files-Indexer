import os
import csv
import asyncio
import random
import re
from user_agent import generate_user_agent
from aiohttp import ClientSession
from bs4 import BeautifulSoup

Words = []
IgnoreWords = []
Formats = ["pdf", "ppt", "doc", "manifest", "txt", "xml"]

Content = {}
MaxWords = 100

Read = {"words.txt": Words, "IgnoreWords.txt": IgnoreWords}

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

for key in Read.keys():
    if os.path.exists(key):
        with open(key, "r") as f:
            Read[key].extend(f.read().split("\n"))

RandomWordsCount = 1

async def get_random_words_from_api():
    API = ["https://random-word-api.herokuapp.com/word"]
    _api = random.choice(API)
    async with ClientSession() as ses:
        for _ in range(RandomWordsCount):
            async with ses.get(_api) as out:
                word = (await out.json())[0]
            while word in IgnoreWords:
                async with ses.get(_api) as out:
                    word = (await out.json())[0]
            Words.append(word)


class EndProgram(Exception):
    ...

async def fetch_files(word):
    if len(Words) == MaxWords:
        raise EndProgram("Limit Reached!")
    print(f"---> Fetching {word}!")
    if word not in IgnoreWords:
        Words.append(word)
    new_task = []
    async with ClientSession() as ses:
        for filetype in Formats:
            url = f"https://google.com/search?q={word}+filetype:{filetype}"

            async def get_page(url_):
                res = await ses.get(
                    url_,
                    headers={
                        "User-Agent": generate_user_agent()
                    },
                )
                ct = await res.read()
                # open("test.html", "wb").write(ct)
                soup = BeautifulSoup(ct, "html.parser", from_encoding="utf-8")
                find = soup.find_all("div", re.compile("egMi0"))
                return find
            get_ = await get_page(url)
            start = 0
            while get_: 
                for res in get_:
                    try:
                        name = res.find("div", re.compile("vvjwJb")).text
                        fileurl = res.find("a", href=re.compile("/url?"))
                        fileurl = fileurl["href"].split("url=")[1].split("&amp")[0].split("&ved=")[0]
                        if Content.get(filetype):
                            Content[filetype].append([name, fileurl])
                        else:
                            Content.update({filetype: [[name, fileurl]]})
                        print(f"--> GOT ---> FROM WORD --> {word}---> {fileurl}")
                        await asyncio.sleep(2)
                        for word_ in name.split():
                            if len(word_) > 3 and word_ not in IgnoreWords:
                                print(f"---> Got new word --> {word_}")
                                new_task.append(fetch_files(word_))
                    except Exception as eR:
                        print(eR)
                if len(get_) == 10:
                    start += 10
                await asyncio.sleep(random.randint(5, 12))
                get_ = await get_page(url + f"&start={start}")
        if new_task:
            await asyncio.gather(*new_task)


async def main():
    print("> Starting UP!")
    await get_random_words_from_api()
#    task = []
    for word in Words:
        await asyncio.sleep(3)
        await fetch_files(word)
#    await asyncio.gather(*task)

try:
    asyncio.run(main())
except (KeyboardInterrupt, EndProgram):
    pass
except Exception as er:
    print(er)

for ft in Content.keys():
    with open(f"{ft.upper()}_files.csv", "a") as f:
        writer = csv.writer(f)
        for line in Content[ft]:
            writer.writerow(line)


IgnoreWords.extend(Words)
with open("IgnoreWords.txt", "w") as f:
    f.write("\n".join(list(set(IgnoreWords))))
