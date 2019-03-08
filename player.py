from game_object import *
from constants import *
from sprite_tools import *

class Player(GameObject):

    def __init__(self, game, x, y):
        GameObject.__init__(self, game, x, y, 5, fps = 4)
        self.mana = 0
        idle = SpriteSheet("will.png", (2, 1), 2)
        self.sprite.add_animation({"Idle": idle})
        self.sprite.start_animation("Idle")
        self.slash = Slash(self.game, 0, 0)
        self.game.movers += [self]
        self.game.effects += [self.slash]
        self.macro = None

        # TODO make this dependent on weapon?
        self.attack_damage = 1

    def update(self, dt):
        GameObject.update(self, dt)
        
    def draw(self, surf):
        GameObject.draw(self, surf)
        
    def translate(self, dx, dy, attack=True):
        if attack and self.attack(dx, dy):
            return True # Able to hit enemy
        if self.map.get((self.x+dx, self.y+dy), ("layer", 4)):
            return False # Enemy blocking square
        return GameObject.translate(self, dx, dy)

    def attack(self, dx, dy, swing_miss=False):
        # TODO generalize this for different weapon types/interactions
        things_hit = self.game.map.get((self.x + dx, self.y + dy), "hittable")
        if len(things_hit) and abs(dx) > 0:
            self.flipped = dx < 0
        for thing in things_hit:
            self.hit(thing)
            self.swing(dx, dy)
        if swing_miss and not things_hit:
            self.swing(dx, dy)
        return len(things_hit)

    def hit(self, thing):
        thing.take_damage(self.attack_damage)
        self.game.camera.shake(0.5)

    def swing(self, dx, dy):
        self.slash.start_slash(self.x+dx, self.y+dy, (dx, dy))
        


