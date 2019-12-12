import pygame
import sys
import time
import os
import random
from math import sin, pi
from sprite_tools import *
from constants import *
from map import Map
from macro import Macro
from block import *
from player import Player
from enemy import *
from editor import *
from character_select import *
from level_preview import *
from map import Wall, Stairs
from copy import deepcopy

EPSILON = 0.5
ALPHA = 0.2
DISCOUNT = 0.95
EXPLORE = 500
EP_DIFF = EPSILON/EXPLORE

class Game(object):

	def __init__(self):
		pygame.mixer.init(44200, -16, 2, 1024)
		pygame.init()

		self.bug_noise = pygame.mixer.Sound("audio/bug.wav")
		self.bat_noise = pygame.mixer.Sound("audio/ebat.wav")
		self.swish_noise = pygame.mixer.Sound("audio/swish.wav")
		self.ram_noise = pygame.mixer.Sound("audio/ram.wav")
		self.firewall_noise = pygame.mixer.Sound("audio/firewall.wav")
		self.byte_noise = pygame.mixer.Sound("audio/byte.wav")
		self.hit_noise = pygame.mixer.Sound("audio/hit.wav")
		self.mus = pygame.mixer.Sound("audio/music.wav")
		self.tile_pickup = pygame.mixer.Sound("audio/pickup_tile.wav")
		self.tile_drop = pygame.mixer.Sound("audio/drop_tile.wav")
		self.stairs_sound = pygame.mixer.Sound("audio/stairs2.wav")
		self.player_move_sound = pygame.mixer.Sound("audio/player_move.wav")
		self.nope = pygame.mixer.Sound("audio/nope.wav")
		self.close_editor = pygame.mixer.Sound("audio/close_editor.wav")
		self.mus.set_volume(0.5)
		self.mus.play(-1)

		self.swish_noise.set_volume(0.7)
		self.nope.set_volume(0.1)
		self.close_editor.set_volume(0.1)
		self.ram_noise.set_volume(0.6)
		self.byte_noise.set_volume(0.4)
		self.bat_noise.set_volume(0.8)
		self.hit_noise.set_volume(0.4)
		self.tile_pickup.set_volume(0.3)
		self.player_move_sound.set_volume(0.00)
		self.screen_blit = pygame.display.set_mode(BLIT_SIZE)
		self.screen = pygame.Surface(WINDOW_SIZE)
		self.editor = Editor(self)
		self.sel = CharacterSelect(self.screen_blit).sel
		self.player = Player(self, 0, 0, idx = self.sel)
		self.camera = Camera()
		self.level = 0
		self.epsilon = EPSILON

		self.black_screen = pygame.Surface(WINDOW_SIZE).convert()
		self.black_screen.fill((0, 0, 0))
		self.black_alpha = 255.0
		self.black_screen.set_alpha(self.black_alpha)
		self.black_shade = DOWN

		self.delay = 0
		self.command_font = pygame.font.SysFont("monospace", 12)
		self.command_rectangles = {}

		self.heart = pygame.image.load("images/heart.png")
		self.hheart = pygame.image.load("images/half_heart.png")
		self.eheart = pygame.image.load("images/empty_heart.png")
		self.heart_width = self.heart.get_width()
		self.macro_frame = pygame.image.load("images/macro_frame.png")

		self.mana_bar = pygame.image.load("images/mana_outer_bar.png")
		self.mana_fill = pygame.image.load("images/mana_inner_bar.png")
		self.display_mana = self.player.mana
		self.empty_tile = pygame.image.load("images/empty_tile_small.png")

		self.values = dict()
		self.last_hp = 0

		self.load_level()


	def update_mana_bar(self, dt):
		dm = self.player.mana - self.display_mana
		self.display_mana += dm * dt * 20.0


	def render_health(self, surf):

		mana = self.player.mana
		max_mana = self.player.mana_max
		surf.blit(self.mana_bar, (11, 30))
		new_width = int(self.display_mana*53//max_mana + 0.5)
		mana_fill = pygame.transform.scale(self.mana_fill, (new_width, self.mana_fill.get_height()))
		surf.blit(mana_fill, (14, 33))
		if True:
			surf.blit(self.macro_frame, (175, 10))
			for i, macro in enumerate(self.player.macros):
				empty = [False, False, False]
				for j, block in (enumerate(macro.blocks) if macro else enumerate(empty)):
					x = j * 13 + 194
					if block:
						surf.blit(block.surf_item, (x, 13 + 17*(i%3)))
		hp = self.player.hp
		xoff = 10
		yoff = 10
		xspace = 20
		for i in range(self.player.hp_max):
			if hp <= 0:
				surf.blit(self.eheart, (xoff + xspace*i, yoff))
			elif hp <= 0.5:
				surf.blit(self.hheart, (xoff + xspace*i, yoff))
			else:
				surf.blit(self.heart, (xoff + xspace*i, yoff))
			hp -= 1


	def getQValue(self, state, action):
		statetup = tuple(state)
		if statetup in self.values and action in self.values[statetup]:
			return self.values[statetup][action]
		else:
			return 0.0

	def getLegalActions(self, state):
		all_legal = [(0,0)]
		for i in range(len(directions)):
			if state[i] != 'wall':
				all_legal.append(directions[i])

		# print(all_legal)
		return all_legal

	def computeValueFromQValues(self, state):
		possibleActions = self.getLegalActions(state)
		if len(possibleActions) == 0:
			return 0.0
		max_act = None
		max_val = None
		q_values = [self.getQValue(state, action)for action in possibleActions]
		return max(q_values)

	def computeActionFromQValues(self, state):
		possibleActions = self.getLegalActions(state)
		if len(possibleActions) == 0:
			return None
		max_act = None
		max_val = None
		q_values = [self.getQValue(state,action) for action in possibleActions]
		action = possibleActions[q_values.index(max(q_values))]
		return action

	def getAction(self, state):
		legalActions = self.getLegalActions(state)
		action = None
		"*** YOUR CODE HERE ***"
		eps = (random.random() <= self.epsilon)
		if eps:
			# print("eps")
			action = random.choice(legalActions)
		else:
			# print("norm")
			action = self.computeActionFromQValues(state)
		return action

	def updateQ(self, state, action, nextState, reward):
		statetup = tuple(state)
		if statetup not in self.values:
			self.values[statetup] = dict()

		if action not in self.values[statetup]:
			self.values[statetup][action] = 0.0

		futureReward = self.computeValueFromQValues(nextState)
		temp_val = (1-ALPHA)*self.getQValue(state,action) + ALPHA*(reward + DISCOUNT*futureReward)
		self.values[statetup][action] = temp_val
		# print(self.values)

	def get_reward(self, state, action, next_state):
		# HP going down is bad
		reward = -5
		if self.last_hp != self.player.hp:
			reward -= 500
			if self.player.hp == 0:
				reward -= 10000
		# Entering stairs is good
		if (self.player.x, self.player.y) == self.stairloc:
			reward += 1000
			self.num_turns -= 500

		# Going towards stairs is good
		if state[-2] == 1 and action[0] == 1:
			reward += 10
		elif state[-2] == -1 and action[0] == -1:
			reward += 10
		elif state[-1] == -1 and action[1] == 1:
			reward += 10
		elif state[-1] == -1 and action[1] == -1:
			reward += 10
		elif state[-2] == 1 and action[0] == -1:
			reward -= 20
		elif state[-2] == -1 and action[0] == 1:
			reward -= 20
		elif state[-1] == -1 and action[1] == -1:
			reward -= 20
		elif state[-1] == -1 and action[1] == 1:
			reward -= 20

		# Killing an enemy is good
		if self.killed_enemy == True:
			reward += 200

		obj = self.map.get((self.player.x + action[0]), (self.player.y + action[1]))
		if issubclass(obj, Enemy):
			if type(obj) == GroundHazard_Fixed or type(obj) == GroundHazard:
				pass
			else:
				if obj.hp < obj.max_hp:
					reward += 50

		# print(reward)
		return reward

	def get_state(self):
		adj_squares = directions
		game_state = ["tile"] * len(all_squares)
		for ind, square in enumerate(all_squares):
			thing_in_square = "empty"
			for obj in self.map.get((self.player.x + square[0], self.player.y + square[1])):
				# print(type(obj))
				# print(type(Wall()))
				# print(Enemy)
				if issubclass(type(obj), Enemy):
					# print("1")
					if type(obj) == GroundHazard_Fixed or type(obj) == GroundHazard:
						thing_in_square = "hazard"
					else:
						if obj.countdown > 0:
							thing_in_square = "enemy" + str(obj.hp)
						else:
							thing_in_square = "attack"
				elif type(obj) == Wall:
					# print("2")
					thing_in_square = "wall"
				elif type(obj) == Stairs:
					# print("3")
					thing_in_square = "stairs"
			game_state[ind] = thing_in_square
		# determine if we moved closer to the stairs

		# compare
		if self.player.x - self.stairloc[0] > 0:
			game_state.append(-1)
		elif self.player.x - self.stairloc[0] < 0:
			game_state.append(1)
		else:
			game_state.append(0)

		if self.player.y - self.stairloc[1] > 0:
			game_state.append(1)
		elif self.player.y - self.stairloc[1] < 0:
			game_state.append(-1)
		else:
			game_state.append(0)

		return game_state

	def handle_events(self, events):
		self.editor.update_mouse_events(events)

		# Extract features from map; map this to a new state
		# print("---------------------------")
		game_state = self.get_state()

		# print(game_state)
		# Get the best event using q-learning
		action = self.getAction(game_state)
		# event = random.choice(ACTIONS)
		if not (self.player.x, self.player.y) == self.stairloc:
			if self.player.hp > 0:
				self.last_hp = self.player.hp
				self.lastloc = (self.player.x, self.player.y)

				self.move_player(action[0], action[1])
				game_state2 = self.get_state()
				reward = 0
				self.killed_enemy = False
				reward = self.get_reward(game_state, action, game_state2)
				self.updateQ(game_state, action, game_state2, reward)
			else:
				self.move_player(action[0], action[1])
				game_state2 = self.get_state()
				reward = 0
				self.killed_enemy = False
				reward = self.get_reward(game_state, action, game_state2)
				self.updateQ(game_state, action, game_state2, reward)

		self.num_turns += 1
		if self.num_turns >= 1000:
			self.player.hp = 0
			self.end_level()
			self.num_turns = 0
			self.episode += 1
			if self.episode < EXPLORE:
				self.epsilon -= EP_DIFF

	def main(self):

		self.episode = 0
		self.num_turns = 0
		self.ep_last_hp = None

		self.dts = []
		then = time.time()
		time.sleep(0.01)
		self.camera.speed = 1.0 #   Change this for slow motion

		while True:
			# Game logic up here
			now = time.time()
			# Change real_dt if you want to let everything jump to stable state
			# If we set it to 1 second, will jump 1 second into future
			real_dt = now - then
			then = now

			dt = self.camera.update(real_dt)
			dt = min(dt, 1/30.0)
			events = pygame.event.get()
			self.handle_events(events)

			# Take turn
			if self.delay > 0:
				self.delay -= dt
			elif len(self.turn_queue) == 0:
				enemies = self.movers[:]
				enemies.remove(self.player)
				self.turn_queue = [self.player] + enemies
				for mover in self.turn_queue:
					mover.turns = 1
			else:
				while len(self.turn_queue) > 0:
					mover = self.turn_queue[0]
					if mover is self.player:
						if mover.turns <= 0: # end player turn
							self.turn_queue.remove(mover)
						elif mover.macro: # run player macro
							if mover.macro.run(self, mover): # end macro
								mover.macro = None
								mover.turns = 0
						break
					else:
						mover.turns -= 1
						if mover.turns <= 0: # end enemy turn
							self.turn_queue.remove(mover)
						if self.map.on_screen(self.camera, mover.x, mover.y):
							if mover in self.movers: # move enemy
								mover.move()
						if self.delay > 0:
							break

			if self.player.hp == 0 and self.ep_last_hp != 0:
				self.episode += 1
				if self.episode < EXPLORE:
					self.epsilon -= EP_DIFF
				print("episode", self.episode)
				self.num_turns = 0


			self.ep_last_hp = self.player.hp

			# Drawing goes here
			# TODO remove fill functions once screen is completely filled with tiles
			# Comment out this and below that has "render" or "draw"; keep "update" to stop drawing things
			for obj in self.movers + self.effects + [self.editor]:
				obj.update(dt)
			self.update_black_screen(dt)
			self.update_mana_bar(dt)
			self.draw_fps(dt)
			self.update_screen()

			if self.episode % 20 == 0 or True:
				self.screen.fill((0, 0, 0))

				self.update_camera_target()
				self.draw_map()

				#self.player.draw(self.screen)
				#self.terminal.draw(self.screen)
				self.render_health(self.screen)
				self.editor.draw(self.screen)

				# Removing this stops driving to screen
				pygame.display.flip()


	def update_black_screen(self, dt):
		rate = 2000 #higher = less black screen
		if self.black_shade == UP:
			self.black_alpha = min(self.black_alpha + rate*dt, 255)
		elif self.black_shade == DOWN:
			self.black_alpha = max(0, self.black_alpha - rate*dt)

		if self.black_alpha == 255 and self.black_shade == UP:
			if self.player.hp > 0:
				self.load_level()
			else:
				self.load_level(game_over=True)


	def draw_map(self):
		x_center, y_center = self.camera.center_tile_pos()
		xlim = (int(x_center - X_GIRTH), int(x_center + X_GIRTH))
		ylim = (int(y_center - Y_GIRTH), int(y_center + Y_GIRTH))
		self.map.draw(self.screen, ylim, xlim)


	def update_camera_target(self):
		self.camera.target_x = self.player.sprite.x_pos - (WINDOW_WIDTH)/2 + TILE_SIZE/2
		self.camera.target_y = self.player.sprite.y_pos - (WINDOW_HEIGHT)/2 + TILE_SIZE/2


	def generate_command_surface(self, text):
		font_render = self.command_font.render(text, 0, (255, 255, 255))
		back_square = pygame.Surface((font_render.get_width(), font_render.get_height()))
		back_square.fill((0, 0, 0))
		back_square.set_alpha(150)
		self.command_renders[text] = font_render
		self.command_rectangles[text] = back_square


	def update_screen(self):
		if self.black_alpha:
			self.black_screen.set_alpha(self.black_alpha)
			self.screen.blit(self.black_screen, (0, 0))
		self.screen_blit.blit(pygame.transform.scale(self.screen, BLIT_SIZE), (0, 0))


	def draw_fps(self, dt):
		self.dts.append(dt)
		if len(self.dts) > 300:
			self.dts = self.dts[-300:]
		dt_avg = sum(self.dts)*1.0/len(self.dts)
		fps = int(1/dt_avg)
		fonty_obj = self.command_font.render("FPS: " + str(fps), 0, (255, 255, 255))
		self.screen_blit.blit(fonty_obj, (WINDOW_WIDTH*SCALE - 60, 10))


	def move_player(self, dx, dy, end_turn=True):
		if self.player.macro or self.editor.active:
			return
		if len(self.turn_queue) and self.turn_queue[0] is self.player:
			self.player.translate(dx, dy)
			self.delay += 0.01
			if end_turn:
				self.player.turns -= 1
				self.player.mana = min(self.player.mana_max, self.player.mana + 1)
				if self.player.turns <= 0: # end player turn
					self.turn_queue.remove(self.player)

	def end_level(self):
		self.black_shade = UP
		self.stairs_sound.play()

	def load_level(self, game_over=False, seed=None):
		random.seed(seed)
		if game_over:
			self.level = 1
			self.editor = Editor(self)
			self.sel = CharacterSelect(self.screen_blit).sel
			self.player = Player(self, 0, 0, self.sel)
			# Add agent dying? Reset agent?
		else:
			self.level += 1
		self.movers = [self.player]
		self.effects = [self.player.slash]
		self.map = Map((30, 30))
		spawn = self.map.populate_path(self, self.level, wall_ratio=0.0)
		self.player.x = spawn[0]
		self.player.y = spawn[1]
		self.player.map = self.map
		self.map.add_to_cell(self.player, (self.player.x,self.player.y))
		self.camera.focus(self.player.x, self.player.y)
		self.turn_queue = []
		self.player.sprite.x_pos = self.player.x * TILE_SIZE
		self.player.sprite.y_pos = self.player.y * TILE_SIZE
		self.player.macro = False

		LevelPreview(self)

		self.black_shade = DOWN
		self.black_alpha = 255.0


class Camera(object):

	def __init__(self):

		self.x = 0
		self.y = 0

		self.target_x = 0
		self.target_y = 0

		self.speed = 1.0

		self.shake_max_amp = 4
		self.shake_amp = 0
		self.shake_t_off = 0
		self.shake_freq = 12
		shake_duration = 0.3
		self.shake_decay = 1.0/shake_duration

		self.t = 0

	def update(self, dt):

		self.t += dt

		dx = self.target_x - self.x
		dy = self.target_y - self.y

		self.x += dx * dt * 20
		self.y += dy * dt * 20

		self.shake_amp *= 0.04**dt

		return dt * self.speed

	def center_tile_pos(self):

		return ((self.x + WINDOW_WIDTH/2)//TILE_SIZE,
				(self.y + WINDOW_HEIGHT/2)//TILE_SIZE)

	def shake(self, amplitude = 1.0):
		self.shake_amp += self.shake_max_amp * amplitude

	def focus(self, x, y):
		self.x = x*TILE_SIZE-WINDOW_WIDTH/2 + TILE_SIZE/2
		self.y = y*TILE_SIZE-WINDOW_HEIGHT/2 + TILE_SIZE/2
		self.target_x = self.x
		self.target_y = self.y

	def get_x(self):
		return self.x

	def get_y(self):
		if self.shake_amp < 1:
			return self.y
		return self.y + sin(self.shake_freq * 2 * pi * self.t)*self.shake_amp


if __name__=="__main__":

	a = Game()
	a.main()
