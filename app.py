import json, config
from flask import Flask, request, jsonify, render_template
from trading_ig import IGService


app = Flask(__name__)

ig_service = IGService(username='fatisy786',password='Images786$',api_key=config.API_KEY_LIVE, acc_type='LIVE')
ig_service.create_session()
account = ig_service.fetch_accounts()

markets = ig_service.search_markets(search_term='nvda')


print(account)
print(markets)

def order(direction, epic, pos_size, order_type, currency):
    try:
        print(f"sending order {order_type} - {direction} {pos_size} {epic}")
        trade = ig_service.create_open_position(
            currency_code=currency,
            direction=direction,
            epic=epic,
            expiry='-',
            guaranteed_stop="false",
            limit_distance=None,
            limit_level=None,
            stop_distance=None,
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
    order_response = order(direction=direction, pos_size=pos_size, epic=epic, order_type=order_type, currency=currenncy_code)

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
