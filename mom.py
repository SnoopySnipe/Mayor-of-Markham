import discord
import sys
import random
import asyncio
from discord.ext import commands
from config import mom_category_id, mom_lobby_id, cards, min_players, max_players, max_hand_size
from objects import Player, Deck, Card, Game

bot = commands.Bot(command_prefix='$')
game = None
message_append = "\n===================="

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('--------------------')
    await bot.change_presence(activity=discord.Game(name='😩🍆💦💦 MeagerThreadbareDogfish'))

@bot.command()
async def start(ctx):
    '''@user1 @user2 @user3 [@user4] [@user5] [$user6]'''
    # check if game was started in lobby
    mom_lobby = bot.get_channel(mom_lobby_id)
    if ctx.channel == mom_lobby:
        # check if there is already a game in progress
        global game
        if game:
            await ctx.send("There is currently a game in progress!")
            return
        # check that we start the game with min-max players
        users = ctx.message.mentions
        if not (min_players <= len(users) <= max_players):
            await ctx.send("Mayor of Markham is a " + str(min_players) + "-" + str(max_players) + " player game!")
            return

        # create a text channel for each player
        mom_category = bot.get_channel(mom_category_id)
        random.shuffle(users)
        i = 1
        players = []
        for user in users:
            overwrites = {
                mom_category.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True)
            }
            channel = await mom_category.create_text_channel("player-" + str(i), overwrites=overwrites)
            players.append({"user":user, "channel":channel})
            i += 1
        
        # initialize game
        game = Game(players)
        for player in players:
            game.do_draw(player["user"], 6, 0, 0)
            await player["channel"].send(game.display_hand(player["user"]) + message_append)
        await mom_lobby.send(game.display_status() + message_append)
        await mom_lobby.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)
        await game.turn.channel.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)
        
@bot.command()
async def discard(ctx, *argv):
    # verify
    if not (game.verify_context(ctx, "players")):
        return
    if not (game.verify_game_state(phase="market", subphase="discard", turn=ctx.author, not_mayor=ctx.author)):
        return
    # get discarded cards
    discard1_cards = []
    discard2_cards = []
    argc = len(argv)
    for i in range(argc):
        if (i < argc and argv[i] == "-d1"):
            j = i + 1
            while (j < argc and argv[j] != "-d2"):
                discard1_cards.append(argv[j])
                j += 1
        elif (i < argc and argv[i] == "-d2"):
            j = i + 1
            while (j < argc):
                discard2_cards.append(argv[j])
                j += 1
    # make sure they are integers >= 1
    try:
        for i in range(len(discard1_cards)):
            discard1_cards[i] = int(discard1_cards[i])
            if discard1_cards[i] < 1:
                await ctx.send("Error: Invalid argument")
                return
        for i in range(len(discard2_cards)):
            discard2_cards[i] = int(discard2_cards[i])
            if discard2_cards[i] < 1:
                await ctx.send("Error: Invalid argument")
                return
    except ValueError:
        await ctx.send("Error: Invalid argument")
        return
    # check that all cards given are unique
    temp = discard1_cards + discard2_cards
    if len(temp) > len(set(temp)):
        await ctx.send("Error: Invalid argument")
        return
    # make sure the player owns these cards
    for card in temp:
        if card > len(game.get_player(ctx.author).hand):
            await ctx.send("Error: Invalid argument")
            return
    # discard the cards
    if game.do_discard(ctx.author, discard1_cards, discard2_cards) is None:
        await ctx.send("Error: Invalid argument")
        return
    # update game state
    game.subphase = "draw"
    # send the discard piles into lobby
    mom_lobby = bot.get_channel(mom_lobby_id)
    await mom_lobby.send("{} discarded {} cards into pile 1 and {} cards into pile 2.".format(ctx.author.name, len(discard1_cards), len(discard2_cards)))
    await mom_lobby.send("**__Discard Pile 1__**\n{}".format(game.discard1.show_cards()))
    await mom_lobby.send("**__Discard Pile 2__**\n{}".format(game.discard2.show_cards()) + message_append)
    await ctx.send(game.display_hand(ctx.author) + message_append)
    await mom_lobby.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)
    await game.turn.channel.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)

@bot.command()
async def endgame(ctx):
    global game
    if game:
        for channel in game.get_channels():
            await channel.delete()
    game = None

@bot.command()
async def inventory(ctx):
    if not (game.verify_context(ctx, "players")):
        return
    p = game.get_player(ctx.author)
    message = "**__{}'s Inventory__**\n**Money:** ${}".format(p.user.name, p.money)
    for item in p.get_items():
        message += "\n**{}** {}".format(p.get_items()[item], item)
    await p.channel.send(message + message_append)
    
@bot.command()
async def data(ctx):
    if not (game.verify_context(ctx, "players")):
        return
    p = game.get_player(ctx.author)
    message = game.card_data()
    await p.channel.send(message + message_append)

@bot.command()
async def draw(ctx, *argv):
    ''''''
    # verify
    if not (game.verify_context(ctx, "players")):
        return
    if not (game.verify_game_state(phase="market", subphase="draw", turn=ctx.author, not_mayor=ctx.author)):
        return
    # get draw amounts
    deck_draw = 0
    discard1_draw = 0
    discard2_draw = 0
    argc = len(argv)
    for i in range(argc):
        if (i < argc and argv[i] == "-d"):
            deck_draw = argv[i+1]
        elif (i < argc and argv[i] == "-d1"):
            discard1_draw = argv[i+1]
        elif (i < argc and argv[i] == "-d2"):
            discard2_draw = argv[i+1]
    # make sure they are integers >= 0
    try:
        deck_draw = int(deck_draw)
        discard1_draw = int(discard1_draw)
        discard2_draw = int(discard2_draw)
    except ValueError:
        await ctx.send("Error: Invalid argument")
        return
    if (deck_draw < 0 or discard1_draw < 0 or discard2_draw < 0):
        await ctx.send("Error: Invalid argument")
        return
    # draw the cards
    if game.do_draw(ctx.author, deck_draw, discard1_draw, discard2_draw) is None:
        await ctx.send("Error: Invalid argument")
        return
    # send the discard piles into lobby
    mom_lobby = bot.get_channel(mom_lobby_id)
    await mom_lobby.send("{} drew {} cards from the deck, {} cards from discard pile 1, and {} cards from discard pile 2.".format(ctx.author.name, deck_draw, discard1_draw, discard2_draw))
    await mom_lobby.send("**__Discard Pile 1__**\n{}".format(game.discard1.show_cards()))
    await mom_lobby.send("**__Discard Pile 2__**\n{}".format(game.discard2.show_cards()) + message_append)
    await ctx.send(game.display_hand(ctx.author) + message_append)
    # update game state
    game.turn_count += 1
    if game.turn_count == len(game.players) - 1:
        game.phase = "submission"
        game.subphase = "submit"
        game.turn = []
        for p in game.players:
            if p != game.mayor:
                game.turn.append(p)
        game.turn_count = 0
        await mom_lobby.send(game.display_status() + message_append)
        for p in game.turn:
            await p.channel.send("{}, please make your {}!".format(p.user.name, game.phase) + message_append)
        await wait_submit(ctx)
    else:
        game.subphase = "discard"
        if game.players.index(game.turn) == len(game.players) - 1:
            game.turn = game.players[0]
        else:
            game.turn = game.players[game.players.index(game.turn) + 1]
        if game.turn == game.mayor:
            if game.players.index(game.turn) == len(game.players) - 1:
                game.turn = game.players[0]
            else:
                game.turn = game.players[game.players.index(game.turn) + 1]
        await mom_lobby.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)

async def wait_submit(ctx):
    if not (game.verify_game_state(phase="submission", subphase="submit")):
        return
    mom_lobby = bot.get_channel(mom_lobby_id)
    def check(m):
        p = game.get_player(m.author)
        verify_context = p is not None and m.channel == p.channel and p in game.turn
        command = m.content.split()
        verify_message = len(command) > 1 and command[0] == "$submit"
        if verify_context and verify_message:
            # make sure they are integers >= 1
            verify_numbers = True
            try:
                for i in range(1, len(command)):
                    command[i] = int(command[i])
                    if command[i] < 1:
                        verify_numbers = False
            except ValueError:
                verify_numbers = False
            # check that all cards given are unique
            if len(command[1:]) > len(set(command[1:])):
                verify_numbers = False
            # make sure the player owns these cards
            for card in command[1:]:
                if card > len(p.hand):
                    verify_numbers = False
            if verify_numbers:
                game.turn.remove(p)
                for card in command[1:]:
                    p.submit.append(p.hand[card-1])
                for card in p.submit:
                    p.hand.remove(card)
        return len(game.turn) == 0

    try:
        msg = await bot.wait_for('message', timeout=600.0, check=check)
    except asyncio.TimeoutError:
        await mom_lobby.send("RIP Mayor of Markham")
    else:
        game.phase = "declaration"
        game.subphase = "declare"
        game.turn = []
        for p in game.players:
            if p != game.mayor:
                game.turn.append(p)
        game.turn_count = 0
        await mom_lobby.send(game.display_status() + message_append)
        for p in game.turn:
            await p.channel.send("{}, please make your {}!".format(p.user.name, game.phase) + message_append)
        await wait_declare(ctx)
        
async def wait_declare(ctx):
    if not (game.verify_game_state(phase="declaration", subphase="declare")):
        return
    mom_lobby = bot.get_channel(mom_lobby_id)
    def check(m):
        p = game.get_player(m.author)
        verify_context = p is not None and m.channel == p.channel and p in game.turn
        command = m.content.split()
        verify_message = len(command) == 3 and command[0] == "$declare"
        if verify_context and verify_message:
            # make sure the number is equal to submission amount
            verify_numbers = True
            try:
                command[1] = int(command[1])
                if command[1] != len(p.submit):
                    verify_numbers = False
            except ValueError:
                verify_numbers = False
            # check that the card exists and is legal
            verify_cards = False
            global cards
            if command[2] in cards:
                if cards[command[2]]["type"] == "legal":
                    verify_cards = True
            if verify_numbers and verify_cards:
                game.turn.remove(p)
                for i in range(command[1]):
                    p.declare.append(Card(cards[command[2]]["name"], cards[command[2]]["value"], cards[command[2]]["penalty"], cards[command[2]]["type"]))
        return len(game.turn) == 0

    try:
        msg = await bot.wait_for('message', timeout=600.0, check=check)
    except asyncio.TimeoutError:
        await mom_lobby.send("RIP Mayor of Markham")
    else:
        game.phase = "inspection"
        game.subphase = "inspect"
        game.turn = []
        for p in game.players:
            if p != game.mayor:
                game.turn.append(p)
        game.turn_count = 0
        await mom_lobby.send(game.display_status() + message_append)
        await wait_inspect(ctx)
        
async def wait_inspect(ctx):
    if not (game.verify_game_state(phase="inspection", subphase="inspect")):
        return
    mom_lobby = bot.get_channel(mom_lobby_id)
    def check(m):
        p = game.get_player(m.author)
        verify_context = p is not None and m.channel == mom_lobby and p == game.mayor
        command = m.content.split()
        verify_message = len(command) == 1 and (command[0] == "$pass" or command[0] == "$check")
        return verify_context and verify_message
    for p in game.turn:
        await mom_lobby.send("{} declared they have {} {}. Mayor {}, will you let them pass or will you check them?".format(p.user.name, p.get_declare()[0], p.get_declare()[1], game.mayor.user.name) + message_append)
        try:
            msg = await bot.wait_for('message', timeout=600.0, check=check)
        except asyncio.TimeoutError:
            await mom_lobby.send("RIP Mayor of Markham")
        else:
            if msg.content.strip() == "$pass":
                for item in p.submit:
                    p.items.append(item)
            elif msg.content.strip() == "$check":
                payout = 0
                check_message = "{}'s submission was:".format(p.user.name)
                for sub in p.get_submit():
                    check_message += "\n{} {}".format(p.get_submit()[sub], sub)
                if p.get_declare()[1] not in p.get_submit() or p.get_declare()[0] != p.get_submit()[p.get_declare()[1]]:
                    for item in p.submit:
                        if item.name != p.get_declare()[1]:
                            payout += item.penalty
                            game.exile.add(item)
                        else:
                            p.items.append(item)
                    p.money -= payout
                    game.mayor.money += payout
                    check_message += "\n{} paid Mayor {} ${}.".format(p.user.name, game.mayor.user.name, payout) + message_append
                    await mom_lobby.send(check_message)
                else:
                    for item in p.submit:
                        payout += item.penalty
                        p.items.append(item)
                    p.money += payout
                    game.mayor.money -= payout
                    check_message += "\nMayor {} paid {} ${}.".format(game.mayor.user.name, p.user.name, payout) + message_append
                    await mom_lobby.send(check_message)
              
            p.submit = []
            p.declare = []
            
    game.round += 1
    if game.round > game.max_rounds:
        await mom_lobby.send("The game is over!" + message_append)
        for p in game.players:
            message = "**__{}'s Inventory__**\n**Money:** ${}".format(p.user.name, p.money)
            for item in p.get_items():
                message += "\n**{}** {}".format(p.get_items()[item], item)
            await mom_lobby.send(message + message_append)
        await mom_lobby.send(game.card_data() + message_append)
        await endgame(ctx)
    else:
        game.phase = "market"
        game.subphase = "discard"
        game.turn_count = 0
        if game.players.index(game.mayor) == len(game.players) - 1:
            game.mayor = game.players[0]
            game.turn = game.players[1]
        else:
            game.mayor = game.players[game.players.index(game.mayor) + 1]
            if game.players.index(game.mayor) == len(game.players) - 1:
                game.turn = game.players[0]
            else:
                game.turn = game.players[game.players.index(game.mayor) + 1]
        for p in game.players:
            await p.channel.send(game.display_hand(p.user) + message_append)
        await mom_lobby.send(game.display_status() + message_append)
        await mom_lobby.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)
        await game.turn.channel.send("{}, it is your turn to {}!".format(game.turn.user.name, game.subphase) + message_append)
        

if (__name__ == "__main__"):
    # go through arguments and find bot token
    argc = len(sys.argv)
    token = None
    for i in range(argc):
        if (i < argc and sys.argv[i] == "-t"):
            token = sys.argv[i+1]
    if token is None:
        print("Error: No token given")
        sys.exit(1)
    print("Logging in...")
    bot.run(token)
