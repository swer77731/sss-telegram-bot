import json
import ssl
import urllib.request
import pandas as pd
import urllib.parse

def send_telegram_message(bot_token, chat_id, message):
    """發送訊息到 Telegram"""
    message_encoded = urllib.parse.quote_plus(message)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message_encoded}&parse_mode=Markdown"
    context = ssl._create_unverified_context()
    try:
        urllib.request.urlopen(url, context=context)
        print("✅ Telegram 訊息已發送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def get_etf_data_and_notify():
    TELEGRAM_BOT_TOKEN = "7791748692:AAELpJ4d1aMKbvL8NTY0Wsm7Imh1pZKY-hM"
    TELEGRAM_CHAT_ID = "-4845859627"
    stockStr = "00982A"
    lookday = "10"

    url = f"https://www.cmoney.tw/api/cm/MobileService/ashx/GetDtnoData.ashx?action=getdtnodata&DtNo=59449513&ParamStr=AssignID%3D{stockStr}%3BMTPeriod%3D0%3BDTMode%3D0%3BDTRange%3D{lookday}%3BDTOrder%3D1%3BMajorTable%3DM722%3B&FilterNo=0"
    context = ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(url, context=context) as jsondata:
            data = json.loads(jsondata.read().decode('utf-8'))

        df = pd.DataFrame(data["Data"], columns=data["Title"])
        df["持有數"] = pd.to_numeric(df["持有數"], errors='coerce').astype("Int64")
        df["日期"] = pd.to_datetime(df["日期"], format='%Y%m%d').dt.date
        
        # 過濾掉非數字的代號
        df = df[df['標的代號'].str.isnumeric()]
        
        df.sort_values(by=["標的代號", "日期"], inplace=True)

        dates = sorted(df['日期'].unique(), reverse=True)
        if len(dates) < 2:
            msg = f"❌ {stockStr} 資料不足，無法比較。"
        else:
            latest, previous = dates[0], dates[1]
            df_recent = df[df['日期'].isin([latest, previous])].copy()
            df_recent['持股變動'] = df_recent.groupby('標的代號')['持有數'].diff()
            df_change = df_recent[df_recent['日期'] == latest].dropna(subset=['持股變動'])
            df_change = df_change[df_change['持股變動'] != 0]

            buys = df_change[df_change['持股變動'] > 0].sort_values('持股變動', ascending=False).head(5)
            sells = df_change[df_change['持股變動'] < 0].sort_values('持股變動', ascending=True).head(5)

            latest_stocks = set(df[df['日期'] == latest]['標的代號'])
            previous_stocks = set(df[df['日期'] == previous]['標的代號'])
            new_stock_codes = latest_stocks - previous_stocks

            if new_stock_codes:
                new_holdings_df = df[(df['日期'] == latest) & (df['標的代號'].isin(new_stock_codes))].sort_values('持有數', ascending=False)
            else:
                new_holdings_df = pd.DataFrame()

            # ---【就是修改這一行，移除了股票代號】---
            msg = f"📅 {latest}\n\n"

            # 新增持股區塊
            msg += "🆕 *新增持股*\n"
            if not new_holdings_df.empty:
                for _, r in new_holdings_df.iterrows():
                    msg += f"`{r['標的代號']:<6} {r['標的名稱']:<5} {int(r['持有數']):,}`\n"
            else:
                msg += "`(無)`\n"

            # 買超區塊
            msg += "\n📈 *買超 Top 5*\n"
            if not buys.empty:
                for _, r in buys.iterrows():
                    msg += f"`{r['標的代號']:<6} {r['標的名稱']:<5} +{int(r['持股變動']):,}`\n"
            else:
                msg += "`(無)`\n"

            # 賣超區塊
            msg += "\n📉 *賣超 Top 5*\n"
            if not sells.empty:
                for _, r in sells.iterrows():
                    msg += f"`{r['標的代號']:<6} {r['標的名稱']:<5} {int(r['持股變動']):,}`\n"
            else:
                msg += "`(無)`\n"

    except Exception as e:
        msg = f"❌ 讀取 {stockStr} 資料發生錯誤: {e}"

    send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

if __name__ == "__main__":
    get_etf_data_and_notify()
