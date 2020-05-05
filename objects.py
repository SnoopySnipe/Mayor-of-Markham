from config import mom_category_id, mom_lobby_id, cards, min_players, max_players, max_hand_size
import random

class Player:
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        self.money = 50
        self.hand = []
        self.items = []
        self.submit = []
        self.declare = []
    
    def get_items(self):
        data = {}
        for card in self.items:
            if card.name in data:
                data[card.name] += 1
            else:
                data[card.name] = 1
        return data
        
    def draw(self, amount, deck):
        if 0 < amount <= deck.get_length():
            for i in range(amount):
                self.hand.append(deck.draw())
            return self.hand
        return None
        
    def get_declare(self):
        return len(self.declare), self.declare[0].name
        
    def get_submit(self):
        data = {}
        for card in self.submit:
            if card.name in data:
                data[card.name] += 1
            else:
                data[card.name] = 1
        return data
        
    def display_hand(self):
        message = "**__Hand__**"
        for i in range(1, len(self.hand) + 1):
            message += "\n**{}**: {}".format(i, self.hand[i - 1])
        return message
        
    def discard(self, cards1, deck1, cards2, deck2):
        for card in cards1:
            if card < 1 or card > len(self.hand):
                return None
        for card in cards2:
            if card < 1 or card > len(self.hand):
                return None

        for card in cards1:
            deck1.add(self.hand[card - 1])
        for card in cards2:
            deck2.add(self.hand[card - 1])
        
        to_remove = cards1 + cards2
        cards_to_remove = []
        for card in to_remove:
            cards_to_remove.append(self.hand[card - 1])
        for card in cards_to_remove:
            self.hand.remove(card)
        
        return self.hand
            
        
class Deck:
    def __init__(self):
        self.cards = []
        
    def add(self, card):
        self.cards.append(card)
        
    def shuffle(self):
        random.shuffle(self.cards)
        
    def draw(self):
        if self.get_length() > 0:
            return self.cards.pop()
        else:
            return None
        
    def get_length(self):
        return len(self.cards)
        
    def show_cards(self):
        message = ""
        i = 0
        for card in self.cards:
            message = "{}\n".format(card) + message
            i += 1
            if i == 10:
                break
        return message
        
class Card:
    def __init__(self, name, value, penalty, type):
        self.name = name
        self.value = value
        self.penalty = penalty
        self.type = type
        
    def __str__(self):
        return "{} --- V:{} --- P:{} --- T:{}".format(self.name, self.value, self.penalty, self.type)
        
class Game:
    def __init__(self, players):
        self.round = 1
        self.phase = "market"
        self.subphase = "discard"
        self.deck = Deck()
        self.discard1 = Deck()
        self.discard2 = Deck()
        self.exile = Deck()
        
        # initialize deck
        for k, v in cards.items():
            for i in range(v["count"]):
                self.deck.add(Card(v["name"], v["value"], v["penalty"], v["type"]))
        self.deck.shuffle()
        
        # initialize players
        self.players = []
        for player in players:
            self.players.append(Player(player["user"], player["channel"]))
        self.mayor = self.players[0]
        self.turn = self.players[1]
        self.turn_count = 0
        self.max_rounds = (max_players + min_players - len(self.players)) * len(self.players)
        
    def get_channels(self):
        ret = []
        for p in self.players:
            ret.append(p.channel)
        return ret
            
    def display_status(self):
        return "Round **{}** of {}: **{}** is the Mayor of Markham! We are on the **{}** phase.".format(self.round, self.max_rounds, self.mayor.user.name, self.phase)
            
    def get_player(self, player):
        for p in self.players:
            if p.user == player:
                return p
        return None
    
    def do_draw(self, player, deck_draw, discard1_draw, discard2_draw):
        p = self.get_player(player)
        if p:
            if len(p.hand) + deck_draw + discard1_draw + discard2_draw == max_hand_size:
                p.draw(deck_draw, self.deck)
                p.draw(discard1_draw, self.discard1)
                p.draw(discard2_draw, self.discard2)
                return p.hand
        return None
    
    def do_discard(self, player, discard1_cards, discard2_cards):
        p = self.get_player(player)
        if p:
            for card in discard1_cards:
                if card < 1 or card > len(p.hand):
                    return None
            for card in discard2_cards:
                if card < 1 or card > len(p.hand):
                    return None
            p.discard(discard1_cards, self.discard1, discard2_cards, self.discard2)
            return p.hand
        return None
        
    def display_hand(self, player):
        p = self.get_player(player)
        if p:
            return p.display_hand()
        return None
        
    def card_data(self):
        message = "**__Legal Goods__**"
        for card in cards:
            if cards[card]["type"] == "legal":
                message += "\n **{}** --- V:{} --- P:{} --- 1B:{} --- 2B:{}".format(cards[card]["name"], cards[card]["value"], cards[card]["penalty"], cards[card]["first_bonus"], cards[card]["second_bonus"])
        message += "\n**__Contraband Goods__**"
        for card in cards:
            if cards[card]["type"] == "contraband":
                message += "\n **{}** --- V:{} --- P:{}".format(cards[card]["name"], cards[card]["value"], cards[card]["penalty"])
        message += "\n**__Royal Goods__**"
        for card in cards:
            if cards[card]["type"] == "royal":
                message += "\n **{}** --- V:{} --- P:{} --- G:{} --- M:{}".format(cards[card]["name"], cards[card]["value"], cards[card]["penalty"], cards[card]["good"], cards[card]["multiplier"])
        return message

    def verify_game_state(self, **kwargs):
        for k, v in kwargs.items():
            if k == "phase":
                if self.phase != v:
                    return False
            elif k == "subphase":
                if self.subphase != v:
                    return False
            elif k == "turn":
                if self.turn.user != v:
                    return False
            elif k == "mayor":
                if self.mayor.user != v:
                    return False
            elif k == "not_turn":
                if self.turn.user == v:
                    return False
            elif k == "not_mayor":
                if self.mayor.user == v:
                    return False
        return True
        
    def verify_context(self, ctx, channels):
        if channels == "lobby":
            if ctx.channel == mom_lobby:
                return True
        elif channels == "players":
            if ctx.channel in self.get_channels():
                return True
        return False