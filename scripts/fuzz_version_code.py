import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import product

import aiohttp

logging.basicConfig(
    filename="debug.log",  # 日志文件路径
    filemode="a",  # 写入模式：'a'追加，'w'覆盖
    level=logging.INFO,  # 设置记录级别（INFO及以上）
    format="[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
)

FIRM_SEARCH_URL = (
    r"https://partners.hikvision.com/support/psp-api/document/firmware/search"
)


@dataclass
class RespJsonData:
    code: str
    upgradePath: str = None
    upgradeVersion: str = None
    downloadId: str = None
    updateTime: str = None
    fileName: str = None
    fileSize: str = None


async def fuzz_for_device(device_id: str, serial_no: str, latest_version: str):
    """
    Fuzz firsion number from the latest to the oldest.
    Auto parse version number like V5.7.101 build 230509
    """

    version_regex = r"V(\d+)\.(\d+)\.(\d+)\s+build\s+(\d+)"
    v1, v2, v3, build = re.match(version_regex, latest_version).groups()
    v1, v2, v3 = int(v1), int(v2), int(v3)

    last_build = date(2000 + int(build[:2]), int(build[2:4]), int(build[4:6]))

    logging.info(
        f"Fuzzing versions for device {device_id} with serial {serial_no} "
        f"starting from {latest_version}"
    )
    async with aiohttp.ClientSession() as session:
        for v1_, v2_, v3_ in product(
            range(v1, -1, -1), range(v2, -1, -1), range(v3, -1, -1)
        ):
            for offset in range(0, 365 * 2, 1):
                build_ = last_build - timedelta(days=offset)
                verfmt = f"V{v1_}.{v2_}.{v3_} build {build_.strftime('%y%m%d')}"
                logging.debug(f"Fuzzing version: {verfmt}")

                payload = {
                    "deviceId": device_id,
                    "serialNo": serial_no,
                    "build": build_.strftime("%y%m%d"),
                    "version1": str(v1_),
                    "version2": str(v2_),
                    "version3": str(v3_),
                    "dataSource": 2,
                }

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6,zh-TW;q=0.5",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
                    ),
                    "sec-ch-ua": 'Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "Windows",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Referer": "https://partners.hikvision.com/support/upgrade/download/detail?serialNo="
                    + serial_no,
                }

                done = False
                while not done:
                    try:
                        async with session.post(
                            FIRM_SEARCH_URL, json=payload, headers=headers
                        ) as response:
                            if response.status != 200:
                                logging.fatal(
                                    f"HTTP failed to fetch for {verfmt}: {response.status}"
                                )
                            else:
                                json_ = await response.json()
                                code = json_.get("code")
                                assert (
                                    code == "000"
                                ), f"Unexpected code {code} in json for {verfmt}, msg= {json_.get('msg')}"

                                data = RespJsonData(**json_.get("data"))
                                if data.code != "-5" and data.code != "-7":
                                    logging.info(
                                        f"Found version: {verfmt} for device {device_id} with serial {serial_no}"
                                    )
                                    logging.info(json_.get("data"))
                                    last_build = build_
                                else:
                                    logging.error(
                                        f"No valid firmware found for {verfmt} "
                                        f"for device {device_id} with serial {serial_no}"
                                    )
                                done = True
                        await asyncio.sleep(0.5)  # 避免请求过于频繁

                    except AssertionError as e:
                        if "过于频繁" in str(e):
                            logging.warning("遇到风控")
                            logging.warning(e)
                            await asyncio.sleep(60)  # 等待60秒后重试
                        else:
                            raise e


def main():
    def fuzz_ball_FT():
        try:
            return fuzz_for_device(
                device_id="16041d8b-a187-4b0b-abc7-3671e9614aa6",
                serial_no="FT9368351",
                latest_version="V5.7.9 build 220520",
            )
        except Exception as e:
            logging.error(f"Error fuzzing Ball FT: {e}")

    def fuzz_gun_GD():
        try:
            return fuzz_for_device(
                device_id="16041d8b-a187-4b0b-abc7-3671e9614aa6",
                serial_no="GD0104139",
                latest_version="V9.9.200 build 250720",
            )
        except Exception as e:
            logging.error(f"Error fuzzing Gun GD: {e}")

    tasks = [fuzz_ball_FT(), fuzz_gun_GD()]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    main()
