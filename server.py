from aiohttp import web
import aiofiles
import asyncio
import argparse
import os
import logging

CHUNK_SIZE = 1024 * 10


async def archive(request):
    name = request.match_info.get("archive_hash", None)

    path = os.path.join(".", args.path, name)
    if not os.path.exists(path):
        logging.error("archive not found")
        raise web.HTTPNotFound(text="Archive not found")

    response = web.StreamResponse()
    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = "attachment; filename='archive.zip'"
    await response.prepare(request)

    try:
        process = await asyncio.create_subprocess_exec(
            "zip",
            "-",
            "-r",
            ".",
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        while chunk := await process.stdout.read(CHUNK_SIZE):  # type: ignore
            await response.write(chunk)
            await asyncio.sleep(args.delay)

    except ConnectionError:
        logging.info("Download interrupted")
    except KeyboardInterrupt:
        await response.write_eof()

    finally:
        if process and process.returncode is None:  # type: ignore
            logging.info("killing zip")
            process.kill()
            await process.communicate()
            response.force_close()
        return response


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image compression service")
    parser.add_argument("--logging", "-l", action="store_true", help="Turn on logging")
    parser.add_argument("--delay", "-d", type=int, default=0, help="Response delay (s)")
    parser.add_argument("--path", default="test_photos", help="path to photos dir")
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archive),
        ]
    )
    web.run_app(app)
