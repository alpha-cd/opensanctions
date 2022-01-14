import io
import csv

from async_timeout import asyncio

from opensanctions import settings
from opensanctions.core import Context
from opensanctions.wikidata import get_entity, entity_to_ftm


async def crawl_qid(context, qid, country):
    if qid is None:
        return
    data = await get_entity(context, qid)
    if data is not None:
        await entity_to_ftm(
            context,
            data,
            position=data.get("position"),
            topics="role.pep",
            country=country,
        )


async def crawl(context: Context):
    text = await context.fetch_text(context.dataset.data.url)
    tasks = []
    for row in csv.DictReader(io.StringIO(text)):
        qid = row.get("personID")
        country = row.get("catalog")
        tasks.append(crawl_qid(context, qid, country))
        # if len(tasks) > 10:
        #     await asyncio.gather(*tasks)
        #     tasks = []

    if len(tasks):
        await asyncio.gather(*tasks)
