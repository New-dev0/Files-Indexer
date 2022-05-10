import os
import csv
import asyncio
import random
import re
import string
from user_agent import generate_user_agent
from aiohttp import ClientSession
from bs4 import BeautifulSoup

Words = []
IgnoreWords = []
IgnoreLinks = []
_Processed = []

Formats = ["pdf", "ppt", "doc", "manifest", "txt", "xml", "mkv"]

_Key = {
    "WordList.txt": Words,
    "IgnoreLinks.txt": IgnoreLinks,
    "IgnoreWords.txt": IgnoreWords,
}

MaxWords = 1

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

for key in _Key.keys():
    if os.path.exists(key):
        with open(key, "r") as f:
            _Key[key].extend(f.read().split("\n"))
        if key == "WordList.txt":
            os.remove(key)


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


def save_files(content, path=""):
    for ft in content.keys():
        with open(f"{path}{ft.upper()}_files.csv", "a") as f:
            writer = csv.writer(f)
            for line in content[ft]:
                writer.writerow(line)


async def fetch_files(word):
    if len(_Processed) == MaxWords:
        raise EndProgram
    if word in IgnoreWords:
        return
    print(f"---> Fetching {word}!")
    IgnoreWords.append(word)
    Content = {}
    new_task = []
    folder = word[0].upper()
    try:
        async with ClientSession() as ses:
            for filetype in Formats:
                url = f"https://google.com/search?q={word}+filetype:{filetype}"

                async def get_page(url_):
                    res = await ses.get(
                      url_,
                        headers={"User-Agent": generate_user_agent()},
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
                            fileurl = (
                            fileurl["href"]
                            .split("url=")[1]
                            .split("&amp")[0]
                            .split("&ved=")[0]
                            .strip()
                            )
                            if fileurl not in IgnoreLinks:
                                if not os.path.exists(folder):
                                    os.mkdir(folder)
                                if Content.get(filetype):
                                    Content[filetype].append([name, fileurl])
                                else:
                                    Content.update({filetype: [[name, fileurl]]})
                                IgnoreLinks.append(fileurl)
                            print(f"--> GOT ---> FROM WORD --> {word}---> {fileurl}")
                            await asyncio.sleep(2)
                            for word_ in name.split():
                                cont = True
                                for c in word_:
                                    if c not in string.ascii_letters:
                                        cont = False
                                        break
                                if cont and len(word_) > 3 and word_ not in IgnoreWords:
                                    print(f"---> Got new word --> {word_}")
                                    new_task.append(fetch_files(word_))
                        except Exception as eR:
                            # raise eR
                            print(eR)
                    if len(get_) == 10:
                        start += 10
                    await asyncio.sleep(random.randint(2, 5))
                    get_ = await get_page(url + f"&start={start}")
            _Processed.append(word)
            if word in Words:
                Words.remove(word)
    except KeyboardInterrupt:
        pass
    if Content:
        word = folder + word[1:]
        if not os.path.exists(folder + f"/{word}"):
            os.mkdir(folder + f"/{word}")
        save_files(Content, path=f"{folder}/{word}/")
    await asyncio.gather(*new_task)


async def main():
    print("> Starting UP!")
    await get_random_words_from_api()
    # task = []
    for word in Words:
        await asyncio.sleep(3)
        await fetch_files(word)
    # await asyncio.gather(*task)


try:
    asyncio.run(main())
except (KeyboardInterrupt, EndProgram):
    pass
except Exception as er:
    # raise er
    print(er)


for _ in _Key.keys():
    with open(_, "w") as f:
        if not _Key[_]:
            os.remove(_)
        else:
            f.write("\n".join(sorted(_Key[_])))
