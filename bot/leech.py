import json
import random
from typing import Dict, List, Optional

import bs4
import discord

import _nhentai
from core import bot


with open("./bot/assets/misc/wordlist.txt", "r", encoding="utf-8") as f:
    wordlist: List[str] = [row.strip("\n") for row in f.readlines()]


def get_word() -> str:
    return random.choice(wordlist)


with open("./bot/assets/misc/fact.txt", "r", encoding="utf-8") as f:
    facts: List[str] = [row.strip("\n") for row in f.readlines()]


def get_fact() -> str:
    return random.choice(facts)


with open("./bot/assets/misc/8ball.txt", "r", encoding="utf-8") as f:
    answers: List[str] = [row.strip("\n") for row in f.readlines()]


def get_8ball() -> str:
    return random.choice(answers)


with open("./bot/assets/misc/quotes.json", "r", encoding="utf-8") as f:
    quotes: List[Dict[str, str]] = json.load(f)


def get_quote() -> discord.Embed:
    quote: Dict[str, str] = random.choice(quotes)
    embed: discord.Embed = discord.Embed(description=quote["quote"])
    embed.set_author(
        name="From " + quote["anime"],
        icon_url=bot.user.avatar.url,
    )
    embed.set_footer(text=quote["character"])
    return embed


async def get_sauce(src: str) -> List[discord.Embed]:
    ret: List[discord.Embed] = []
    async with bot.session.post("https://saucenao.com/search.php", data={"url": src}) as response:
        if response.ok:
            html: str = await response.text(encoding="utf-8")
            soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html, "html.parser")
            results: bs4.element.ResultSet[bs4.BeautifulSoup] = soup.find_all(name="div", class_="result")
            count: int = 1

            for result in results:
                if len(ret) == 6:
                    break

                try:
                    if "hidden" in result.get("class"):
                        break

                    result = result.find(
                        name="table",
                        attrs={"class": "resulttable"}
                    )

                    image_url: str = result.find(
                        name="div",
                        attrs={"class": "resultimage"}
                    ).find(name="img").get("src")

                    url: str = result.find(
                        name="div",
                        attrs={"class": "resultcontentcolumn"}
                    ).find(name="a").get("href")

                    similarity: str = result.find(
                        name="div",
                        attrs={"class": "resultsimilarityinfo"}
                    ).get_text()

                    em: discord.Embed = discord.Embed(title=f"Displaying result #{count}")
                    em.add_field(
                        name="Sauce",
                        value=url,
                        inline=False,
                    )
                    em.add_field(
                        name="Similarity",
                        value=similarity,
                        inline=False,
                    )
                    em.set_thumbnail(url=image_url)
                    ret.append(em)
                    count += 1
                except BaseException:
                    continue

        return ret
