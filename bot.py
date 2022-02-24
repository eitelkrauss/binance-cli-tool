import typer, sqlite3, json
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *


app = typer.Typer()

public_client = Client("", "")

try:
    dbconn = sqlite3.connect('bot.db')
except sqlite3.Error as error:
    typer.echo("Problema conectando a la base de datos: '{}'".format(error))
else:
    dbcursor = dbconn.cursor()


#balance minimo para operar
MINIMUM_TRADING_BALANCE = 10


@app.command()
def startdb():

    dbcursor.execute("""
                CREATE TABLE users(
                    username text,
                    api_id text,
                    api_secret text,
                    balance real,
                    positions text
                )
                """)

    dbconn.commit()


    # dbcursor.execute("""
    #             CREATE TABLE positions(
    #                 symbol text,
    #                 entry real,
    #                 close real,
    #                 pnl real,
    #                 status text
    #             )
    #             """)

    # dbconn.commit()

    dbconn.close()




# USERS COMMANDS

@app.command()
def adduser():
    username = typer.prompt("Enter username")
    api_id = typer.prompt("Enter API id")
    api_secret = typer.prompt("Enter API secret")
    binance_client = Client(api_id, api_secret)
    try:
        res = binance_client.get_asset_balance(asset='USDT')
    except BinanceAPIException as e:
        typer.echo("Problema con la cuenta en Binance: '{}'".format(e))
    else:
        typer.echo("Conectado con la cuenta.\nRecibiendo balance.\n")
        balance = res['free']
        typer.echo("USDT: '{}'".format(balance))
    with dbconn:
        dbcursor.execute("INSERT INTO users VALUES ('{}', '{}', '{}', '{}', null)".format(username, api_id, api_secret, balance))
        typer.echo("Agregando user '{}'".format(username))






@app.command()
def listusers():
    dbcursor.execute("SELECT * FROM users")
    desc = dbcursor.description
    column_names = [col[0] for col in desc]
    data = [dict(zip(column_names, row)) for row in dbcursor]
    typer.echo(data)



@app.command()
def finduser(username):
    dbcursor.execute("SELECT * FROM users WHERE username = :username", {'username': username})
   
    #if dbcursor.fetchall():
     #   data = intodict(dbcursor.description, dbcursor.fetchall())
      #  typer.echo("Username: '{}'\nAPI id: xxxx\nAPI secret: xxxx\nBalance: '{}' USDT".format(data[0]['username'], data[0]['balance']))
    user = dbcursor.fetchone()
    if user:
        typer.echo("Username: '{}'\nAPI id: xxxx\nAPI secret: xxxx\nBalance: '{}' USDT".format(user[0], user[3]))
    else:
        typer.echo("No existe usuarios con ese username\n")
        


@app.command()
def deleteuser(username: str):
    with dbconn:
        dbcursor.execute("DELETE FROM users WHERE username = :username", {'username': username})
    
    typer.echo("Borrando user '{}'".format(username))







# TRADING DATA


@app.command()
def gettrades(symbol: str):
    res = public_client.get_recent_trades(symbol=symbol)

    for trade in res:
        typer.echo(trade["qty"] + " @ " + trade["price"])





# TRADING COMMANDS


@app.command()
def buy():
    dbcursor.execute("SELECT * FROM users WHERE balance > '{}'".format(MINIMUM_TRADING_BALANCE))
    users = dbcursor.fetchall()
    users_data = intodict(dbcursor.description, users)

    # try:
    #     info = public_client.get_symbol_info(symbol)
    # except BinanceAPIException as e:
    #     typer.echo("Problema con info del simbolo: '{}'".format(e))
    # else:
    #     percent_price_multup = 0.0
    #     percent_price_multdown = 0.0
    #     for filter in info['filters']:
    #         if filter['filterType'] == 'PERCENT_PRICE':
    #             percent_price_multup = float(filter["multiplierUp"])
    #             percent_price_multdown = float(filter["multiplierDown"])
        
    #     typer.echo(percent_price_multup)
    #     typer.echo(percent_price_multdown)
    
    #if price < price * percent_price_multup and price > price * percent_price_multdown:
    #else:
    #   typer.echo("Filter failure: PERCENT_PRICE\n")

    symbol = typer.prompt("Enter symbol (ex. BTCUSDT)")
    size = typer.prompt("Enter size (ex. 1.2)")

    for user in users_data:
        binance_client = Client(user['api_id'], user['api_secret'])
        try:
            order = binance_client.create_test_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=size
            )
        except BinanceAPIException as e:
            typer.echo("Problemas con la orden del usuario '{}': '{}'".format(user['username'], e))
        else:
            typer.echo("Success\n")
            typer.echo(order)

            # save position to DB

            new_position = {"symbol": symbol, "size": float(size)}


            with dbconn:
                if user['positions']:

                    positions = json.loads(user['positions'])

                    old_position = False

                    for position in positions:
                        if symbol == position['symbol']:
                            position["size"] += new_position["size"]
                            old_position = True
                    
                    if not old_position:
                        positions.append(new_position)
                        
                    updated_positions = json.dumps(positions)
                else:
                    positions_list = [new_position]
                    updated_positions = json.dumps(positions_list)

                dbcursor.execute("UPDATE users SET positions = (?) WHERE username = (?)", (updated_positions, user['username']))
                print(updated_positions)






@app.command()
def sell():
    symbol = typer.prompt("Enter symbol (ex. BTCUSDT)")
    dbcursor.execute("SELECT * FROM users WHERE positions > ''")
    users = dbcursor.fetchall()
    users_data = intodict(dbcursor.description, users)

    # try:
    #     info = public_client.get_symbol_info(symbol)
    # except BinanceAPIException as e:
    #     typer.echo("Problema con info del simbolo: '{}'".format(e))
    # else:
    #     percent_price_multup = 0.0
    #     percent_price_multdown = 0.0
    #     for filter in info['filters']:
    #         if filter['filterType'] == 'PERCENT_PRICE':
    #             percent_price_multup = float(filter["multiplierUp"])
    #             percent_price_multdown = float(filter["multiplierDown"])
        
    #     typer.echo(percent_price_multup)
    #     typer.echo(percent_price_multdown)
    
    #if price < price * percent_price_multup and price > price * percent_price_multdown:
    #else:
    #   typer.echo("Filter failure: PERCENT_PRICE\n")

    
    for user in users_data:
        size = 0.0
        user_positions = json.loads(user['positions'])
        for position in user_positions:
            if symbol == position['symbol']:
                size = position['size']
                #new_position_size = position['size'] - size
                #if not new_position_size > 0:   
                print("'{}' has a current position in '{}' is of size '{}'".format(user['username'], symbol, size))
                print("selling here")

        binance_client = Client(user['api_id'], user['api_secret'])
        try:
            order = binance_client.create_test_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=size
            )
        except BinanceAPIException as e:
            typer.echo("Problemas con la orden: '{}'".format(e))
        else:
            typer.echo("Success\n")
            typer.echo(order)

        new_positions = [pos for pos in user_positions if not symbol in pos.values()]
        print(new_positions)
        with dbconn:
            updated_positions = json.dumps(new_positions)
            dbcursor.execute("UPDATE users SET positions = (?) WHERE username = (?)", (updated_positions, user['username']))



@app.command()
def savepositions(symbol: str, size: float):
    positions = 3
    position = {"symbol": symbol, "size": size}
    positions_total = []
    for i in range(positions):
        positions_total.append(position)
    
    typer.echo("Number of positions: '{}'.\nPositions array: '{}'".format(positions, positions_total))
    typer.echo(json.dumps(positions_total))




# Helper functions



# turn query into dictionary
def intodict(desc, cursor_data):
    column_names = [col[0] for col in desc]
    data = [dict(zip(column_names, row)) for row in cursor_data]
    return data






if __name__ == "__main__":
    app()

 