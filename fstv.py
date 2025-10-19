import re
import sys
import asyncio
import random
from playwright.async_api import async_playwright

EPG_URL = "https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive3.xml.gz"
CHANNEL_MAPPING = {
    "usanetwork": {"name": "USA Network", "tv_id": "USA.Network.HD.us2", "group": "USA", "keywords": ["usanetwork"]},
    "cbsla": {"name": "CBS Los Angeles", "tv_id": "KCBS-DT.us_locals1", "logo": "http://drewlive24.duckdns.org:9000/Logos/CBS.png", "group": "USA", "keywords": ["cbslosangeles"]},
    "nbc": {"name": "NBC", "tv_id": "WNBC-DT.us_locals1", "group": "USA", "keywords": ["usnbc"]},
    "abc": {"name": "ABC", "tv_id": "KABC-DT.us_locals1", "group": "USA", "keywords": ["usaabc"]},
    "foxla": {"name": "Fox Los Angeles", "tv_id": "KTTV-DT.us_locals1", "logo": "http://drewlive24.duckdns.org:9000/Logos/FOX.png", "group": "USA", "keywords": ["foxchannel"]},
    "ion": {"name": "ION USA", "tv_id": "ION.Television.HD.us2", "group": "USA", "keywords": ["ionusa"]},
    "telemundo": {"name": "Telemundo", "tv_id": "KVEA-DT.us_locals1", "group": "USA", "keywords": ["usatelemundo"]},
    "unimas": {"name": "UniMás", "tv_id": "KFTH-DT.us_locals1", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/unimas-us.png?raw=true", "group": "USA", "keywords": ["usaunimas"]},
    "tnt": {"name": "TNT", "tv_id": "TNT.HD.us2", "group": "USA", "keywords": ["tntusa"]},
    "paramount": {"name": "Paramount Network", "tv_id": "Paramount.Network.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/paramount-network-hz-us.png?raw=true", "group": "USA", "keywords": ["paramountnetwork"]},
    "axstv": {"name": "AXS TV", "tv_id": "AXS.TV.us2", "group": "USA", "keywords": ["axstv"]},
    "trutv": {"name": "truTV", "tv_id": "truTV.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/tru-tv-us.png?raw=true", "group": "USA", "keywords": ["trutv"]},
    "tbs": {"name": "TBS", "tv_id": "TBS.HD.us2", "group": "USA", "keywords": ["tbs"]},
    "discovery": {"name": "Discovery Channel", "tv_id": "Discovery.Channel.HD.us2", "group": "USA", "keywords": ["zentdiscovery"]},
    "nbcnews": {"name": "NBC News", "tv_id": "plex.tv.NBC.News.NOW.plex", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/nbc-news-flat-us.png?raw=true", "group": "USA News", "keywords": ["nbcnewyork"]},
    "msnbc": {"name": "MSNBC", "tv_id": "MSNBC.HD.us2", "group": "USA News", "keywords": ["usmsnbc"]},
    "cnbc": {"name": "CNBC", "tv_id": "CNBC.HD.us2", "group": "USA News", "keywords": ["usacnbc"]},
    "cnn": {"name": "CNN", "tv_id": "CNN.HD.us2", "group": "USA News", "keywords": ["uscnn"]},
    "foxnews": {"name": "FoxNews", "tv_id": "Fox.News.Channel.HD.us2", "group": "USA News", "keywords": ["usafoxnews", "usfoxnews"]},
    "espn2": {"name": "ESPN2", "tv_id": "ESPN2.HD.us2", "group": "USA Sports", "keywords": ["usespn2"]},
    "espnu": {"name": "ESPNU", "tv_id": "ESPNU.HD.us2", "group": "USA Sports", "keywords": ["usuespn"]},
    "espnnews": {"name": "ESPNews", "tv_id": "ESPNEWS.HD.us2", "group": "USA Sports", "keywords": ["usespnnews"]},
    "secnetwork": {"name": "SEC Network", "tv_id": "SEC.Network.HD.us2", "group": "USA Sports", "keywords": ["usaespnsecnetwork"]},
    "espndeportes": {"name": "ESPN Deportes", "tv_id": "ESPN.Deportes.HD.us2", "group": "USA Sports", "keywords": ["usespndeportes"]},
    "tennis2": {"name": "Tennis Channel 2", "tv_id": "Tennis.Channel.HD.us2", "group": "USA Sports", "keywords": ["ustennistv2"]},
    "cbsgolazo": {"name": "CBS Sports Golazo!", "tv_id": "plex.tv.CBS.Sports.Golazo.Network.plex", "group": "USA Sports", "keywords": ["cbsgolazo"]},
    "cbssports": {"name": "CBS Sports Network", "tv_id": "CBS.Sports.Network.HD.us2", "group": "USA Sports", "keywords": ["usacbssport"]},
    "nflnetwork": {"name": "NFL Network", "tv_id": "NFL.Network.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/nfl-network-hz-us.png?raw=true", "group": "USA Sports", "keywords": ["usnfl"]},
    "nflredzone": {"name": "NFL RedZone", "tv_id": "NFL.RedZone.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/nfl-red-zone-hz-us.png?raw=true", "group": "USA Sports", "keywords": ["usredzone"]},
    "espn": {"name": "ESPN", "tv_id": "ESPN.HD.us2", "group": "USA Sports", "keywords": ["usespn"]},
    "fs1": {"name": "FS1", "tv_id": "FS1.HD.us2", "group": "USA Sports", "keywords": ["usafs1"]},
    "fs2": {"name": "FS2", "tv_id": "FS2.HD.us2", "group": "USA Sports", "keywords": ["usafs2"]},
    "golf": {"name": "Golf Channel", "tv_id": "Golf.Channel.HD.us2", "group": "USA Sports", "keywords": ["usagolf"]},
    "tennis": {"name": "Tennis Channel", "tv_id": "Tennis.Channel.HD.us2", "group": "USA Sports", "keywords": ["ustennistv"]},
    "nbcuniverso": {"name": "NBC Universo", "tv_id": "UNIVERSO.HD.us2", "group": "USA Sports", "keywords": ["usauniverso"]},
    "beinsports": {"name": "BeIN Sports USA", "tv_id": "beIN.Sports.USA.HD.us2", "group": "USA Sports", "keywords": ["beinsporthd"]},
    "beinsportsxtra": {"name": "BeIN Sports Xtra USA", "tv_id": "KSKJ-CD.us_locals1", "group": "USA Sports", "keywords": ["beinsportxtra"]},
    "beinsportses": {"name": "BeIN Sports Español", "tv_id": "613759", "group": "USA Sports", "keywords": ["beinsportespanol"]},
    "beinsportsesxtra": {"name": "BeIN Sports Español Xtra", "tv_id": "613759", "group": "USA Sports", "keywords": ["beinespanolxtra"]},
    "bignetwork": {"name": "Big Ten Network", "tv_id": "Big.Ten.Network.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/big-ten-network-us.png?raw=true", "group": "USA Sports", "keywords": ["usabignetwork"]},
    "fubosports": {"name": "Fubo Sports USA", "tv_id": "Fubo.Sports.us", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/fubo-sports-network-us.png?raw=true", "group": "USA Sports", "keywords": ["usafubosport"]},
    "foxsoccerplus": {"name": "Fox Soccer Plus", "tv_id": "Fox.Soccer.Plus.HD.us2", "group": "USA Sports", "keywords": ["usafoxsoccerplus"]},
    "tycsports": {"name": "TyC Sports", "tv_id": "TyC.Sports.Internacional.USA.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/argentina/tyc-sports-ar.png?raw=true", "group": "USA Sports", "keywords": ["usatycsport"]},
    "marqueesports": {"name": "Marquee Sports Network", "tv_id": "Marquee.Sports.Network.HD.us2", "group": "USA Sports", "keywords": ["usamarqueesportnetwork"]},
    "yesnetwork": {"name": "YES Network USA", "tv_id": "Yes.Network.us2", "group": "USA Sports", "keywords": ["yesusa"]},
    "tudn": {"name": "TUDN", "tv_id": "TUDN.us2", "group": "USA Sports", "keywords": ["usatudn"]},
    "nhlnetwork": {"name": "NHL Network", "tv_id": "NHL.Network.HD.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/nhl-network-us.png?raw=true", "group": "USA Sports", "keywords": ["usnhlnetwork"]},
    "willowhd": {"name": "Willow Cricket HD", "tv_id": "Willow.Cricket.HD.us2", "group": "USA Sports", "keywords": ["uswillowhd"]},
    "willowxtra": {"name": "Willow Xtra", "tv_id": "Willow.Xtra.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/willow-xtra-us.png?raw=true", "group": "USA Sports", "keywords": ["uswillowxtra"]},
    "nbatv": {"name": "NBA TV", "tv_id": "NBA.TV.HD.us2", "logo": "http://drewlive24.duckdns.org:9000/Logos/NBATV.png", "group": "USA Sports", "keywords": ["usnbatv"]},
    "mlbnetwork": {"name": "MLB Network", "tv_id": "MLB.Network.HD.us2", "group": "USA Sports", "keywords": ["usmlbnetwork"]},
    "accnetwork": {"name": "ACC Network", "tv_id": "ACC.Network.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/acc-network-us.png?raw=true", "group": "USA Sports", "keywords": ["usaccnetwork"]},
    "wfn": {"name": "World Fishing Network", "tv_id": "World.Fishing.Network.HD.(US).us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/world-fishing-network-us.png?raw=true", "group": "USA Sports", "keywords": ["uswfn"]},
    "fightnetwork": {"name": "The Fight Network", "tv_id": "Fight.Network.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/fight-network-us.png?raw=true", "group": "USA Sports", "keywords": ["usfightnetwork"]},
    "foxdeportes": {"name": "Fox Deportes", "tv_id": "Fox.Deportes.HD.us2", "group": "USA Sports", "keywords": ["foxdeportes"]},
    "goltv": {"name": "GOL TV", "tv_id": "GOL.TV.us2", "group": "USA Sports", "keywords": ["goltv"]},
    "fandueltv": {"name": "FanDuel TV", "tv_id": "FanDuel.TV.us", "group": "USA Sports", "keywords": ["fandueltv"]},
    "itv1": {"name": "ITV 1 UK", "tv_id": "ITV1.HD.uk", "group": "UK", "keywords": ["ukitv1"]},
    "itv2": {"name": "ITV 2 UK", "tv_id": "ITV2.HD.uk", "group": "UK", "keywords": ["ukitv2"]},
    "itv3": {"name": "ITV 3 UK", "tv_id": "ITV3.HD.uk", "group": "UK", "keywords": ["ukitv3"]},
    "itv4": {"name": "ITV 4 UK", "tv_id": "ITV4.HD.uk", "group": "UK", "keywords": ["ukitv4"]},
    "bbcone": {"name": "BBC One UK", "tv_id": "BBC.One.EastHD.uk", "group": "UK", "keywords": ["ukbbcone"]},
    "bbctwo": {"name": "BBC Two UK", "tv_id": "BBC.Two.HD.uk", "group": "UK", "keywords": ["ukbbctwo"]},
    "bbcnews": {"name": "BBC News UK", "tv_id": "BBC.NEWS.HD.uk", "group": "UK", "keywords": ["ukbbcnews"]},
    "tntsports1": {"name": "TNT Sports 1", "tv_id": "TNT.Sports.1.HD.uk", "group": "UK Sports", "keywords": ["tntsport1"]},
    "tntsports2": {"name": "TNT Sports 2", "tv_id": "TNT.Sports.2.HD.uk", "group": "UK Sports", "keywords": ["tntsport2"]},
    "tntsports3": {"name": "TNT Sports 3", "tv_id": "TNT.Sports.3.HD.uk", "group": "UK Sports", "keywords": ["tntsport3"]},
    "tntsports4": {"name": "TNT Sports 4", "tv_id": "TNT.Sports.4.HD.uk", "group": "UK Sports", "keywords": ["tntsport4"]},
    "tntsports5": {"name": "TNT Sports 5", "tv_id": "TNT.Sports.Ultimate.uk", "group": "UK Sports", "keywords": ["tntsport5"]},
    "eurosport1uk": {"name": "Eurosport 1 UK", "tv_id": "Eurosport.es", "group": "UK Sports", "keywords": ["ukeurosport1"]},
    "eurosport2uk": {"name": "Eurosport 2 UK", "tv_id": "Eurosport.2.es", "group": "UK Sports", "keywords": ["ukeurosport2"]},
    "skysportsgolf": {"name": "Sky Sport Golf UK", "tv_id": "SkySp.Golf.HD.uk", "group": "UK Sports", "keywords": ["ukskysportgolf"]},
    "skysportstennis": {"name": "Sky Sport Tennis UK", "tv_id": "SkySp.Tennis.HD.uk", "group": "UK Sports", "keywords": ["ukskysporttennis"]},
    "mutv": {"name": "MUTV UK", "tv_id": "MUTV.HD.uk", "group": "UK Sports", "keywords": ["ukmutv"]},
    "laligatv": {"name": "La Liga TV UK", "tv_id": "LA.LIGA.za", "group": "UK Sports", "keywords": ["uklaliga"]},
    "skysportsplus": {"name": "Sky Sport Plus UK", "tv_id": "SkySp.PL.HD.uk", "group": "UK Sports", "keywords": ["skysportplus"]},
    "skysportsfootball": {"name": "Sky Sport Football", "tv_id": "SkySp.Fball.HD.uk", "group": "UK Sports", "keywords": ["ukfootball"]},
    "skysportspremier": {"name": "Sky Sport Premier League UK", "tv_id": "SkyPremiereHD.uk", "group": "UK Sports", "keywords": ["ukskysportpremierleague"]},
    "skysportsmix": {"name": "Sky Sport Mix UK", "tv_id": "SkySp.Mix.HD.uk", "group": "UK Sports", "keywords": ["skysportmix"]},
    "skysportsmain": {"name": "Sky Sports Main Event", "tv_id": "SkySpMainEvHD.uk", "group": "UK Sports", "keywords": ["ukmainevent"]},
    "skysportsracing": {"name": "Sky Sport Racing UK", "tv_id": "SkySp.Racing.HD.uk", "group": "UK Sports", "keywords": ["ukskysportracing"]},
    "premiersports1": {"name": "Premier Sports 1 UK", "tv_id": "Premier.Sports.1.HD.uk", "group": "UK Sports", "keywords": ["ukpremiersport1"]},
    "premiersports2": {"name": "Premier Sports 2 UK", "tv_id": "Premier.Sports.2.HD.uk", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-kingdom/premier-sports-2-uk.png?raw=true", "group": "UK Sports", "keywords": ["ukpremiersport2"]},
    "racingtv": {"name": "Racing TV UK", "tv_id": "Racing.TV.HD.uk", "group": "UK Sports", "keywords": ["ukracingtv"]},
    "skysportsf1": {"name": "Sky Sport F1 UK", "tv_id": "SkySp.F1.HD.uk", "group": "UK Sports", "keywords": ["ukskysportf1"]},
    "skysportsarena": {"name": "Sky Sport Arena UK", "tv_id": "Sky.Sports+.Dummy.us", "group": "UK Sports", "keywords": ["skysportarena"]},
    "skysportsaction": {"name": "Sky Sports Action UK", "tv_id": "SkySp.ActionHD.uk", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-kingdom/sky-sports-action-hz-uk.png?raw=true", "group": "UK Sports", "keywords": ["ukskysportaction"]},
    "skysportscricket": {"name": "Sky Sport Cricket UK", "tv_id": "SkySpCricket.HD.uk", "group": "UK Sports", "keywords": ["ukskysportcricket"]},
    "skysportsnews": {"name": "Sky Sport News UK", "tv_id": "SkySp.News.HD.uk", "group": "UK Sports", "keywords": ["ukskysportnews"]},
    "skysportsdarts": {"name": "Sky Sport Darts UK", "tv_id": "Sky.Sports+.Dummy.us", "group": "UK Sports", "keywords": ["ukskysportdarts"]},
    "lfctv": {"name": "LFC TV UK", "tv_id": "LFCTV.HD.uk", "group": "UK Sports", "keywords": ["uklfctv"]},
    "daznuk": {"name": "DAZN 1 UK", "tv_id": "DAZN.Dummy.us", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/germany/dazn1-de.png?raw=true", "group": "UK Sports", "keywords": ["ukdazn"]},
    "wnetwork": {"name": "W Network", "tv_id": "W.Network.HD.ca2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/canada/w-network-ca.png?raw=true", "group": "Canada", "keywords": ["uswnetwork"]},
    "onesoccer": {"name": "OneSoccer Canada", "tv_id": "One.Soccer.ca2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/canada/one-soccer-ca.png?raw=true", "group": "Canada Sports", "keywords": ["caonesoccer"]},
    "tsn1": {"name": "TSN 1", "tv_id": "TSN.1.ca2", "group": "Canada Sports", "keywords": ["tsn1"]},
    "tsn2": {"name": "TSN 2", "tv_id": "TSN.2.ca2", "group": "Canada Sports", "keywords": ["tsn2"]},
    "tsn3": {"name": "TSN 3", "tv_id": "TSN.3.ca2", "group": "Canada Sports", "keywords": ["tsn3"]},
    "tsn4": {"name": "TSN 4", "tv_id": "TSN.4.ca2", "group": "Canada Sports", "keywords": ["tsn4"]},
    "tsn5": {"name": "TSN 5", "tv_id": "TSN.5.ca2", "group": "Canada Sports", "keywords": ["tsn5"]},
    "dazn1de": {"name": "DAZN 1 Germany", "tv_id": "DAZN.1.de", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/germany/dazn1-de.png?raw=true", "group": "Germany", "keywords": ["dedazn1"]},
    "dazn2de": {"name": "DAZN 2 Germany", "tv_id": "DAZN.2.de", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/germany/dazn2-de.png?raw=true", "group": "Germany", "keywords": ["dedazn2"]},
    "skytopde": {"name": "Sky DE Top Event", "tv_id": "Sky.Sport.Top.Event.de", "group": "Germany Sports", "keywords": ["ori2deskydetopent"]},
    "skypremde": {"name": "Sky Sport Premier League DE", "tv_id": "Sky.Sport.Premier.League.de", "group": "Germany Sports", "keywords": ["eplskydepre"]},
    "sportdigitalde": {"name": "SportDigital Germany", "tv_id": "sportdigital.Fussball.de", "group": "Germany Sports", "keywords": ["desportdigital"]},
    "skynewsde": {"name": "Sky Sport News DE", "tv_id": "Sky.Sport.News.de", "group": "Germany Sports", "keywords": ["deskydenews"]},
    "skymixde": {"name": "Sky Mix DE", "tv_id": "Sky.Sport.Mix.de", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-kingdom/sky-mix-uk.png?raw=true", "group": "Germany Sports", "keywords": ["deskydemix"]},
    "bundesliga1": {"name": "Bundesliga 1 Germany", "tv_id": "Sky.Sport.Bundesliga.de", "group": "Germany Sports", "keywords": ["debundesliga1"]},
    "fox502": {"name": "Fox Sports 502 AU", "tv_id": "FoxCricket.au", "group": "Australia Sports", "keywords": ["fox502"]},
    "benficatv": {"name": "Benfica TV", "tv_id": "Benfica.TV.fr", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Logo_Benfica_TV.png/1200px-Logo_Benfica_TV.png", "group": "Portugal Sports", "keywords": ["ptbenfica"]},
    "sporttv1": {"name": "Sport TV1 Portugal", "tv_id": "SPORT.TV1.HD.pt", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/portugal/sport-tv-1-pt.png?raw=true", "group": "Portugal Sports", "keywords": ["ptsporttv1"]},
    "cinemax": {"name": "Cinemax", "tv_id": "Cinemax.HD.us2", "group": "Movies", "keywords": ["zentcinemax"]},
    "hbo2": {"name": "HBO 2", "tv_id": "HBO2.HD.us2", "group": "Movies", "keywords": ["usahbo2"]},
    "hbo": {"name": "HBO", "tv_id": "HBO.East.us2", "logo": "https://github.com/tv-logo/tv-logos/blob/main/countries/united-states/hbo-us.png?raw=true", "group": "Movies", "keywords": ["usahbo"]},
}

MIRRORS = [
    "https://fstv.zip/live-tv.html?timezone=America%2FDenver",
    "https://fstv.online/live-tv.html?timezone=America%2FDenver",
    "https://fstv.space/live-tv.html?timezone=America%2FDenver",
]

MAX_RETRIES = 2

def normalize_channel_name(name: str) -> str:
    cleaned_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return cleaned_name.strip().lower()

def prettify_name(raw: str) -> str:
    raw = re.sub(r'VE[-\s]*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\([^)]*\)', '', raw)
    raw = re.sub(r'[^a-zA-Z0-9\s]', '', raw)
    return re.sub(r'\s+', ' ', raw.strip()).title()

async def fetch_fstv_channels():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"
        )
        await context.set_extra_http_headers({
            "origin": "https://fstv.space",
            "referer": "https://fstv.space"
        })

        page = await context.new_page()
        context.on("page", lambda popup: asyncio.create_task(popup.close()))

        channels_data = []
        visited_urls = set()

        for url in MIRRORS:
            try:
                print(f"🌐 Trying {url}...", flush=True)
                await page.goto(url, timeout=120000, wait_until="domcontentloaded")
                await page.wait_for_selector(".item-channel", timeout=30000)

                all_elements = await page.query_selector_all(".item-channel")
                if not all_elements:
                    print(f"⚠️ No channels found on {url}", flush=True)
                    continue

                for i, element in enumerate(all_elements, start=1):
                    raw_name = await element.get_attribute("title")
                    if not raw_name:
                        continue

                    normalized_name = normalize_channel_name(raw_name)

                    mapped_info = {}
                    for channel_data in CHANNEL_MAPPING.values():
                        if any(keyword in normalized_name for keyword in channel_data.get("keywords", [])):
                            mapped_info = channel_data
                            break

                    new_name = mapped_info.get("name", prettify_name(raw_name))
                    tv_id = mapped_info.get("tv_id", "")
                    logo = mapped_info.get("logo", await element.get_attribute("data-logo"))
                    group_title = "FSTV"

                    last_m3u8_url = None

                    for attempt in range(1, MAX_RETRIES + 1):
                        request_captured = asyncio.Event()

                        async def handle_request(request):
                            nonlocal last_m3u8_url
                            if ".m3u8" in request.url and "auth_key" in request.url:
                                try:
                                    resp = await request.response()
                                    if resp and resp.status == 200:
                                        last_m3u8_url = request.url
                                        if not request_captured.is_set():
                                            request_captured.set()
                                except:
                                    pass

                        page.on("request", handle_request)

                        print(f"👆 Clicking on {new_name} ({i}/{len(all_elements)}) [Attempt {attempt}]...", flush=True)
                        await element.click(force=True, timeout=10000)
                        await asyncio.sleep(random.uniform(2, 4))

                        try:
                            await asyncio.wait_for(request_captured.wait(), timeout=20.0)
                            break
                        except asyncio.TimeoutError:
                            print(f"⚠️ Attempt {attempt} failed for {new_name}", flush=True)
                            await asyncio.sleep(random.uniform(1, 2))
                        finally:
                            page.remove_listener("request", handle_request)

                    if last_m3u8_url and last_m3u8_url not in visited_urls and "false" not in last_m3u8_url.lower():
                        channels_data.append({
                            "url": last_m3u8_url,
                            "logo": logo,
                            "name": new_name,
                            "tv_id": tv_id,
                            "group": group_title
                        })
                        visited_urls.add(last_m3u8_url)
                        print(f"✅ Added {new_name} → {last_m3u8_url}", flush=True)
                    else:
                        print(f"❌ Skipping {new_name}: No valid URL after {MAX_RETRIES} attempts", flush=True)

                print(f"🎉 Successfully processed all channels from {url}", flush=True)
                await browser.close()
                return channels_data

            except Exception as e:
                print(f"❌ Failed on {url}: {e}", flush=True)
                continue

        await browser.close()
        raise Exception("❌ All mirrors failed")

def build_playlist(channels_data):    
    lines = [f'#EXTM3U url-tvg="{EPG_URL}"\n\n']
    for ch in channels_data:
        tvg_id = f' tvg-id="{ch["tv_id"]}"' if ch["tv_id"] else ""
        tvg_name = f' tvg-name="{ch["name"]}"'
        logo = f' tvg-logo="{ch["logo"]}"' if ch["logo"] else ""
        group = f' group-title="{ch["group"]}"'
        lines.append(f'#EXTINF:-1{tvg_id}{tvg_name}{logo}{group},{ch["name"]}\n')
        lines.append(
            '#EXTVLCOPT:http-origin=https://fstv.space/\n'
            '#EXTVLCOPT:http-referrer=https://fstv.space/\n'
            '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0\n'
        )
        lines.append(ch["url"] + "\n")
    return lines

async def main():
    try:
        print("🚀 Starting FSTV scraping...", flush=True)
        channels_data = await fetch_fstv_channels()

        if channels_data:
            channels_data = [ch for ch in channels_data if ch.get("url") and "false" not in ch["url"].lower()]

            playlist = build_playlist(channels_data)
            with open("out/FSTV.m3u8", "w", encoding="utf-8") as f:
                f.writelines(playlist)
            print("🎯 Playlist created: FSTV24.m3u8", flush=True)
        else:
            print("🚫 No channels were scraped.", flush=True)
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
