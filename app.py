import json, config
from flask import Flask, request, jsonify, render_template
from trading_ig import IGService
import traceback
import pandas as pd

app = Flask(__name__)

#fatisy786
#Images786$
def IG_connect():
    ig_service = IGService(username='fatisy123',password='Daniel123$', api_key=config.API_KEY_DEMO, acc_type='DEMO')
    ig_service.create_session()
    return ig_service


def open_trade(direction, epic, pos_size, order_type, currency, stop_level_distance, conn):
    try:
        print(f"sending order {order_type} - {direction} {pos_size} {epic}")
        trade = conn.create_open_position(
            currency_code=currency,
            direction=direction,
            epic=epic,
            expiry='-',
            guaranteed_stop="true",
            limit_distance=None,
            limit_level=None,
            stop_distance=stop_level_distance,
            stop_level=None,
            trailing_stop=None,
            trailing_stop_increment=None,
            force_open="true",
            level=None,
            order_type=order_type,
            size=pos_size,
            quote_id=None
        )
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return trade


def check_open_positions(epic, conn):
    df = conn.fetch_open_positions()
    if not df.empty:
        is_trade = epic in df['epic'].unique()
        direction = df.iloc[0]['direction']
        dealId = df.iloc[0]['dealId']

    else:
        is_trade = False
        direction = None
        dealId = None

    return is_trade, direction, dealId


def close_trade(direction, dealId, pos_size, epic, conn):
    try:
        print(f"sending closing order {dealId} - {direction} {pos_size} {epic}")
        trade = conn.close_open_position(
            direction=direction,
            deal_id=dealId,
            expiry='-',
            order_type='MARKET',
            size=pos_size,
            epic=None,
            level=None,
            quote_id=None
        )
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return trade


def calculate_stoploss_distance(epic, direction, conn):
    # Consultar el minimo % del stop
    epic_rules = conn.fetch_market_by_epic(epic=epic)

    # extract daily low price and high price (float)
    low_price = epic_rules['snapshot']['low']
    high_price = epic_rules['snapshot']['high']
    # extract minimum stop loss distance in %
    min_stop_dist = epic_rules['dealingRules']['minControlledRiskStopDistance']['value'] * 1.5

    if direction == 'BUY':
        stop_level = ((100 - min_stop_dist) * low_price) / 100
        stop_level_points = (low_price - stop_level) * 100

    elif direction == 'SELL':
        stop_level = ((100 + min_stop_dist) * high_price) / 100
        stop_level_points = (stop_level - high_price) * 100

    return stop_level_points


@app.route('/')
def welcome():
    return render_template('index.html')


@app.route('/webhook', methods=['POST'])
def webhook():
    # print(request.data)
    data = json.loads(request.data)

    if data['passphrase'] != config.WEBHOOK_PASSPHRASE:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    direction = data["order_action"]
    print(direction)
    pos_size = data["size"]
    print(pos_size)
    epic = data["ticker"]
    print(epic)
    order_type = data["order_type"]
    currenncy_code = data["currency"]

    connection = IG_connect()
    open_trades, direction_open_trades, dealId = check_open_positions(epic, connection)
    if open_trades is True:
        if direction_open_trades == direction:
            return {
                "code": "not possible",
                "message": "trade in same direction"
            }

        if direction_open_trades != direction:
            # close the open trade
            close_trade(direction=direction, dealId=dealId, pos_size=pos_size, epic=epic, conn=connection)
            # open a new trade according to signal
            stop_level = calculate_stoploss_distance(epic=epic, direction=direction, conn = connection)
            order_response = open_trade(direction=direction, pos_size=pos_size, epic=epic, order_type=order_type,
                                        currency=currenncy_code, stop_level_distance = stop_level, conn=connection)

            # Check if order was succesful
            if order_response:
                return {
                    "code": "success",
                    "message": "order executed"
                }
            else:
                print("order failed")

                return {
                    "code": "error",
                    "message": "order failed"
                }
        else:
            print('Something weird happened!')

    else:
        # prepare a new order calculating stop loss level
        stop_level = calculate_stoploss_distance(epic=epic, direction=direction, conn=connection)
        # Create the new order
        order = open_trade(direction=direction, pos_size=pos_size, epic=epic, order_type=order_type,
                           currency=currenncy_code, stop_level_distance=stop_level, conn=connection)
        if order:
            return {
                "code": "success",
                "message": "order executed"
            }
        else:
            print("order failed")

            return {
                "code": "error",
                "message": "order failed"
            }
