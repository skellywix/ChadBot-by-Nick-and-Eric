import random
import time


class Food:

    def __init__(self, name, color, hp_regen):
        self.name = name
        self.color = color
        self.hp_regen = hp_regen


class Items:

    def __init__(self, name):
        self.name = name


class Character:

    def __init__(self, name, hp, dmg, speed, defense, items=[], alive=True):
        """ This function initializes a class/object with the attribute values passed in the arguments. """
        self.name = name
        self.hp = hp
        self.dmg = dmg
        self.speed = speed
        self.defense = defense
        self.alive = alive
        self.items = items
        if self.hp <= 1:
            self.alive = False

    def attack(self, target):
        dmg_dealt = self.dmg - target.defense
        target.hp -= dmg_dealt
        if target.hp <= 1:
            target.alive = False
        print(f'{self.name} attacks {target.name}, dealing {dmg_dealt} damage!')

    def eat(self, food):
        print(f'{self.name} eats {food.name}, healing {food.hp_regen} hp!')

    def drink_speed_potion(self):
        self.speed = self.speed * 1.5
        print(f'{self.name} drinks speed potion, increasing speed!')


def check_status(character):
    if character.alive:
        status = 'alive'
    else:
        status = 'dead :('
    print(f'{character.name} has {character.hp} health, and is {status}')


banana = Food('banana', 'yellow', 15)
strawberry = Food('strawberry', 'red', 10)
ninja = Character('Ninja', 60, 40, 50, 10)
warrior = Character('Warrior', 100, 30, 30, 15)
dragon = Character('Dragon', 1000, 150, 100, 80)

playable_characters = [ninja, warrior, dragon]
adventures = ['Princess Rescue', 'Goblin Village', 'Evil Witch']
##################################

player_name = None
player_character = None
mission = None


def character_status(n, char):
    print(f'{n+1}. {char.name}')
    print(f'health: {char.hp}   damage: {char.dmg}   speed: {char.speed}   defense: {char.defense}')
    print()


def game_start(test_mode=True):
    global player_name
    print(f'Welcome to Super Fun Adventure!')
    if not test_mode:
        player_name = input('What is your name, adventurer? ')
    else:
        player_name = 'player'
    print(f'Get ready for an amazing adventure, {player_name}!')
    print()


def choose_character():
    global player_character
    print('Choose your character: ')
    print()
    for n, character in enumerate(playable_characters):
        character_status(n, character)
    choice = None
    attempt_count = 0
    while choice not in list(range(1, len(playable_characters) + 1)):
        if attempt_count < 1:
            choice = input('Enter character number: ')
        if 1 < attempt_count <= 5:
            choice = input('Invalid choice! Enter valid number: ')
        if attempt_count > 5:
            choice = input('Are you fucking dumb?!?! Enter valid number: ')
        attempt_count += 1
        try:
            choice = int(choice)
        except ValueError:
            pass
    player_character = playable_characters[choice - 1]
    print(f'You have chosen {player_character.name}')
    print()


def choose_mission():
    global adventures
    print('Choose your adventure: ')
    print()
    for n, adventure in enumerate(adventures):
        print(f'{n+1}. {adventure}')
    print()
    choice = None
    attempt_count = 0
    while choice not in list(range(1, len(playable_characters) + 1)):
        if attempt_count < 1:
            choice = input('Enter adventure: ')
        if 1 < attempt_count <= 5:
            choice = input('Invalid choice! Enter valid number: ')
        if attempt_count > 5:
            choice = input('Are you fucking dumb?!?! Enter valid number: ')
        attempt_count += 1
        try:
            choice = int(choice)
        except ValueError:
            pass
    adventure = adventures[choice - 1]
    print(f'You have chosen {adventure}')
    print()


def start_mission():
    pass


def run_game():
    game_start()
    choose_character()
    choose_mission()


if __name__ == "__main__":
    run_game()
