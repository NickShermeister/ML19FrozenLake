"""
All original code from https://gist.github.com/gkhayes/3d154e0505e31d6367be22ed3da2e955
Written by gkhayes
"""

import numpy as np
import gym
import matplotlib.pyplot as plt

# Import and initialize Mountain Car Environment
env = gym.make('MountainCar-v0')
# env = gym.make('CartPole-v1')
env.reset()


def custom_step(env, action):
    import math
    assert env.action_space.contains(action), "%r (%s) invalid" % (action, type(action))

    position, velocity = env.state
    velocity += (action-1)*env.force + math.cos(3*position)*(-env.gravity)
    velocity = np.clip(velocity, -env.max_speed, env.max_speed)
    position += velocity
    position = np.clip(position, env.min_position, env.max_position)
    if (position==env.min_position and velocity<0): velocity = 0

    done = bool(position >= env.goal_position and velocity >= env.goal_velocity)
    # print(done)
    reward = -1.0

    env.state = (position, velocity)
    return np.array(env.state), reward, done, {}

# Define Q-learning function
def QLearning(env, learning, discount, epsilon, min_eps, episodes):
    # Determine size of discretized state space
    num_states = (env.observation_space.high - env.observation_space.low)*\
                    np.array([10, 100])
    print('env observation space diff: ',(env.observation_space.high - env.observation_space.low))
    print('num_states: ',num_states)

    # it looks like num states is trying to discretize the number of states the car can be in
    # from a continuous state space to a discrete state space

    # the observation space is constrained by the agents min position ,max position
    # as well as min speed and max speed

    print('env.observation_space:', env.observation_space)
    print('env observation space high:',env.observation_space.high)
    print('env observation space low:', env.observation_space.low)
    print('num_states:', num_states)
    num_states = np.round(num_states, 0).astype(int) + 1
    print('num_states:',num_states)

    # Initialize Q table
    Q = np.random.uniform(low = -1, high = 1,
                          size = (num_states[0], num_states[1],
                                  env.action_space.n))
    # action space contains 0,1,2 - Discrete(3) object has 3 states
    # print(Q.shape)
    # Q table is 19x15x3, 19x15 states, 3 actions


    # Initialize variables to track rewards
    reward_list = []
    ave_reward_list = []

    # Calculate episodic reduction in epsilon
    reduction = (epsilon - min_eps)/episodes

    # import sys
    # sys.exit(0)

    # Run Q learning algorithm
    for i in range(episodes):
        # Initialize parameters
        done = False
        tot_reward, reward = 0,0
        state = env.reset()

        # Discretize state
        state_adj = (state - env.observation_space.low)*np.array([10, 100])
        state_adj = np.round(state_adj, 0).astype(int)

        while done != True:
            # Render environment for last five episodes
            if i >= (episodes - 20):
                env.render()

            # Determine next action - epsilon greedy strategy
            if np.random.random() < 1 - epsilon:
                action = np.argmax(Q[state_adj[0], state_adj[1]])
            else:
                action = np.random.randint(0, env.action_space.n)

            # Get next state and reward
            state2, reward, done, info = env.step(action)
            # state2, reward, done, info = custom_step(env, action)

            # Discretize state2
            state2_adj = (state2 - env.observation_space.low)*np.array([10, 100])
            state2_adj = np.round(state2_adj, 0).astype(int)

            #Allow for terminal states
            if done and state2[0] >= 0.5:
                Q[state_adj[0], state_adj[1], action] = reward

            # Adjust Q value for current state
            else:
                delta = learning*(reward +
                                 discount*np.max(Q[state2_adj[0],
                                                   state2_adj[1]]) -
                                 Q[state_adj[0], state_adj[1],action])
                Q[state_adj[0], state_adj[1],action] += delta

            # Update variables
            tot_reward += reward
            state_adj = state2_adj

        # Decay epsilon
        if epsilon > min_eps:
            epsilon -= reduction

        # Track rewards
        reward_list.append(tot_reward)

        if (i+1) % 100 == 0:
            ave_reward = np.mean(reward_list)
            ave_reward_list.append(ave_reward)
            reward_list = []

        if (i+1) % 100 == 0:
            print('Episode {} Average Reward: {}'.format(i+1, ave_reward))

    env.close()

    return ave_reward_list

# Run Q-learning algorithm
rewards = QLearning(env, 0.2, 0.9, 0.8, 0, 5000)

# Plot Rewards
plt.plot(100*(np.arange(len(rewards)) + 1), rewards)
plt.xlabel('Episodes')
plt.ylabel('Average Reward')
plt.title('Average Reward vs Episodes')
plt.savefig('rewards.jpg')
plt.close()
