import random
from enum import IntEnum
from typing import List, Optional, Tuple

class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

class Card:
    def __init__(self, rank: Rank, suit: str):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        rank_names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8',
                     9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        return f"{rank_names[self.rank]}{self.suit}"

    def __eq__(self, other):
        return self.rank == other.rank

class Player:
    def __init__(self, name: str):
        self.name = name
        self.hand: List[Card] = []
        self.face_up: List[Card] = []
        self.face_down: List[Card] = []

    def has_cards(self) -> bool:
        return len(self.hand) > 0 or len(self.face_up) > 0 or len(self.face_down) > 0

    def get_playable_cards(self) -> List[Card]:
        """Returns the current playable cards based on game state"""
        if self.hand:
            return self.hand
        elif self.face_up:
            return self.face_up
        elif self.face_down:
            return self.face_down
        return []

    def is_playing_blind(self) -> bool:
        """Check if player is playing face-down cards (blind)"""
        return len(self.hand) == 0 and len(self.face_up) == 0 and len(self.face_down) > 0

class CardGame:
    def __init__(self, num_players: int):
        if num_players < 2 or num_players > 5:
            raise ValueError("Game supports 2-5 players")

        self.num_players = num_players
        self.players: List[Player] = [Player(f"Player {i+1}") for i in range(num_players)]
        self.deck: List[Card] = []
        self.pile: List[Card] = []
        self.current_player_idx = 0
        self.skips_remaining = 0  # Track how many turns to skip
        self.ace_attack_target: Optional[int] = None  # Target player index for Ace attack
        self.initialize_deck()

    def initialize_deck(self):
        """Create a standard 52-card deck"""
        suits = ['♠', '♥', '♦', '♣']
        self.deck = [Card(Rank(rank), suit) for suit in suits for rank in range(2, 15)]
        random.shuffle(self.deck)

    def setup_game(self):
        """Deal cards to players according to game rules"""
        # Deal 3 face-down cards to each player
        for player in self.players:
            player.face_down = [self.deck.pop() for _ in range(3)]

        # Deal 6 cards to each player's hand
        for player in self.players:
            player.hand = [self.deck.pop() for _ in range(6)]

        # Players choose 3 cards from hand to place face-up
        for player in self.players:
            print(f"\n{player.name}'s hand: {player.hand}")
            print("Choose 3 cards to place face-up (enter indices 0-5, separated by spaces):")

            # Auto-select lowest 3 cards for now (can be made interactive)
            sorted_hand = sorted(enumerate(player.hand), key=lambda x: x[1].rank)
            indices = [sorted_hand[i][0] for i in range(3)]

            for idx in sorted(indices, reverse=True):
                player.face_up.append(player.hand.pop(idx))

            print(f"{player.name}'s face-up cards: {player.face_up}")

    def draw_cards(self, player: Player):
        """Draw cards to maintain minimum 3 in hand while deck is available"""
        while len(player.hand) < 3 and self.deck:
            player.hand.append(self.deck.pop())

    def get_pile_top_rank(self) -> Optional[int]:
        """Get the rank of the top card in the pile"""
        if not self.pile:
            return None
        return self.pile[-1].rank

    def can_play_card(self, card: Card, is_blind: bool = False, is_ace_defense: bool = False) -> bool:
        """Check if a card can be played on the current pile"""
        if not self.pile:
            return True

        # Special handling for Ace attack defense
        if is_ace_defense:
            # Only 2, 10, 3, or Ace can be played in defense
            return card.rank in [Rank.TWO, Rank.TEN, Rank.THREE, Rank.ACE]

        # 10s can always be played (they burn the pile)
        if card.rank == Rank.TEN:
            return True

        # 2s can always be played (they reset to zero)
        if card.rank == Rank.TWO:
            return True

        # 3s can always be played (they mirror the card below)
        if card.rank == Rank.THREE:
            return True

        # Aces can always be played (they attack)
        if card.rank == Rank.ACE:
            return True

        # When playing blind, any card can be attempted
        if is_blind:
            return True

        top_rank = self.get_pile_top_rank()

        # 7 rule: if top card is 7, must play 7 or lower
        if top_rank == Rank.SEVEN:
            return card.rank <= Rank.SEVEN

        # Normal rule: must play equal or higher
        return card.rank >= top_rank

    def check_for_burn(self) -> bool:
        """Check if pile should be burned (4 of same rank in a row or 10 played)"""
        if not self.pile:
            return False

        # Check if last card is a 10
        if self.pile[-1].rank == Rank.TEN:
            return True

        # Check for 4 of the same rank in a row
        if len(self.pile) >= 4:
            last_four = self.pile[-4:]
            if all(card.rank == last_four[0].rank for card in last_four):
                return True

        return False

    def play_turn(self) -> bool:
        """Execute one turn. Returns True if game continues, False if game is over"""
        player = self.players[self.current_player_idx]

        if not player.has_cards():
            print(f"{player.name} has won!")
            return False

        # Handle skip turns (from 8s)
        if self.skips_remaining > 0 and self.ace_attack_target is None:
            print(f"\n{'='*50}")
            print(f"{player.name}'s turn - SKIPPED (8 was played)")
            self.skips_remaining -= 1
            self.current_player_idx = (self.current_player_idx + 1) % self.num_players
            return True

        print(f"\n{'='*50}")
        print(f"{player.name}'s turn")
        print(f"Pile top: {self.pile[-1] if self.pile else 'Empty'}")
        print(f"Pile size: {len(self.pile)}")

        # Check if this is an Ace attack defense turn
        is_defending_ace = self.ace_attack_target == self.current_player_idx

        playable_cards = player.get_playable_cards()
        is_blind = player.is_playing_blind()

        if is_blind:
            print(f"Playing blind from face-down cards!")
        elif is_defending_ace:
            print(f"⚔️ UNDER ATTACK! Must defend with 2, 10, 3, or Ace!")
            print(f"Your cards: {playable_cards}")
        else:
            print(f"Your cards: {playable_cards}")

        # Get player's card selection
        selected_cards = self.get_player_move(player, playable_cards, is_blind, is_defending_ace)

        if selected_cards is None:
            # Player must pick up the pile
            print(f"{player.name} picks up the pile ({len(self.pile)} cards)")
            player.hand.extend(self.pile)
            self.pile = []
            self.ace_attack_target = None
            self.current_player_idx = (self.current_player_idx + 1) % self.num_players
            return True

        # Play the selected cards
        for card in selected_cards:
            self.pile.append(card)
            if card in player.hand:
                player.hand.remove(card)
            elif card in player.face_up:
                player.face_up.remove(card)
            elif card in player.face_down:
                player.face_down.remove(card)

        print(f"{player.name} plays: {selected_cards}")

        # Handle special card effects
        played_rank = selected_cards[0].rank
        num_cards = len(selected_cards)

        # Handle Ace attack
        if played_rank == Rank.ACE and not is_defending_ace:
            # Choose target (auto-select next player for now)
            target_idx = (self.current_player_idx + 1) % self.num_players
            self.ace_attack_target = target_idx
            print(f"💥 {player.name} attacks {self.players[target_idx].name} with Ace!")
            # Draw cards if needed
            self.draw_cards(player)
            # Move to target player
            self.current_player_idx = target_idx
            return True

        # Handle Ace counter-attack
        if played_rank == Rank.ACE and is_defending_ace:
            # Choose new target (auto-select next player)
            target_idx = (self.current_player_idx + 1) % self.num_players
            self.ace_attack_target = target_idx
            print(f"🔄 {player.name} counters with Ace! Now attacking {self.players[target_idx].name}!")
            # Draw cards if needed
            self.draw_cards(player)
            # Move to new target
            self.current_player_idx = target_idx
            return True

        # Handle 2 (resets pile to zero)
        if played_rank == Rank.TWO and is_defending_ace:
            print(f"🛡️ {player.name} defends with 2! Attack blocked!")
            self.ace_attack_target = None

        # Handle 3 (mirrors card below)
        if played_rank == Rank.THREE and is_defending_ace:
            print(f"🪞 {player.name} mirrors with 3! Attack reflected!")
            # 3 mirrors the card below it (the Ace), so it becomes an Ace attack
            target_idx = (self.current_player_idx + 1) % self.num_players
            self.ace_attack_target = target_idx
            print(f"💥 Attack now targets {self.players[target_idx].name}!")
            # Draw cards if needed
            self.draw_cards(player)
            # Move to new target
            self.current_player_idx = target_idx
            return True

        # Clear ace attack if 10 is played
        if played_rank == Rank.TEN:
            self.ace_attack_target = None

        # Check if pile should be burned
        if self.check_for_burn():
            print(f"🔥 BURN! {player.name} burns the pile and plays again!")
            self.pile = []
            self.ace_attack_target = None
            # Same player goes again (don't increment current_player_idx)
        else:
            # Handle 8s (skip next player)
            if played_rank == Rank.EIGHT:
                self.skips_remaining = num_cards
                print(f"⏭️ Next {num_cards} turn(s) will be skipped!")

            # Clear ace attack after successful defense
            if is_defending_ace:
                self.ace_attack_target = None

            # Draw cards if needed
            self.draw_cards(player)
            # Move to next player
            self.current_player_idx = (self.current_player_idx + 1) % self.num_players

        return True

    def get_player_move(self, player: Player, playable_cards: List[Card], is_blind: bool, is_defending_ace: bool = False) -> Optional[List[Card]]:
        """Get the player's move. Returns None if they must pick up the pile"""
        if not playable_cards:
            return None

        # If playing blind, pick one random card
        if is_blind:
            card = random.choice(playable_cards)
            # When blind, check all special card rules
            if not self.pile:
                return [card]

            top_rank = self.get_pile_top_rank()
            # Check if card can be played
            if (card.rank >= top_rank or
                card.rank in [Rank.TWO, Rank.THREE, Rank.TEN, Rank.ACE] or
                (top_rank == Rank.SEVEN and card.rank <= Rank.SEVEN)):
                return [card]
            else:
                print(f"Blind card {card} can't be played!")
                return None

        # Find valid cards to play
        valid_cards = [card for card in playable_cards if self.can_play_card(card, is_blind=False, is_ace_defense=is_defending_ace)]

        if not valid_cards:
            return None

        # Group cards by rank
        rank_groups = {}
        for card in valid_cards:
            if card.rank not in rank_groups:
                rank_groups[card.rank] = []
            rank_groups[card.rank].append(card)

        # If defending against Ace, prioritize defensive cards
        if is_defending_ace:
            # Priority: 2 (blocks), 10 (burns), Ace (counters), 3 (mirrors)
            for rank in [Rank.TWO, Rank.TEN, Rank.ACE, Rank.THREE]:
                if rank in rank_groups:
                    return rank_groups[rank]

        # Auto-play: choose the lowest valid rank, play all cards of that rank
        lowest_rank = min(rank_groups.keys())
        return rank_groups[lowest_rank]

    def play_game(self):
        """Main game loop"""
        self.setup_game()

        print("\n" + "="*50)
        print("GAME START!")
        print("="*50)

        while True:
            if not self.play_turn():
                break

            # Remove players who have no cards left
            self.players = [p for p in self.players if p.has_cards()]
            if len(self.players) <= 1:
                break

            # Adjust current player index if needed
            self.current_player_idx = self.current_player_idx % len(self.players)

        print("\n" + "="*50)
        print("GAME OVER!")
        print("="*50)

if __name__ == "__main__":
    print("Welcome to the Card Game!")
    num_players = int(input("Enter number of players (2-5): "))

    game = CardGame(num_players)
    game.play_game()
