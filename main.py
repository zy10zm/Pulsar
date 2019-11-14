import os
import sys
from mpi4py import MPI

from rmleague.league import League
from environment.envs.simple import make_env
from environment.envhandler import EnvHandler


def main():
    """
    Trains the AlphaStar league.
    This main function acts as the coordinator for rmleague.
    """
    rmleague = League()

    n_agents = 1
    actor_procs = 1
    learner_procs = 1

    sub_comms = []
    actor_lower_bounds = []
    actor_upper_bounds = []

    for idx in range(n_agents):
        actor_lower_bound = idx * (actor_procs + learner_procs)
        actor_upper_bound = idx * (actor_procs + learner_procs) + actor_procs
        learner_bound = idx * (actor_procs + learner_procs) + actor_procs + learner_procs - 1

        actor_lower_bounds.append(actor_lower_bound)
        actor_upper_bounds.append(actor_upper_bound)

        sub_comm  = MPI.COMM_SELF.Spawn_multiple([sys.executable, sys.executable],
                                                 args=[
                                                        ['actor.py', str(idx), str(0.95), str(0.99), str(learner_bound)],
                                                        ['learner.py', str(idx), str(actor_lower_bound), str(actor_upper_bound)]
                                                      ],
                                                 maxprocs=[actor_procs, learner_procs]
                                                )
        sub_comms.append(sub_comm)

        agent = rmleague.get_player_agent(idx)
        sub_comm.send(agent, dest=learner_bound)

        player = rmleague.get_player(idx)
        opponent, tf = player.get_match()
        for ai in range(actor_lower_bound, actor_upper_bound):
            sub_comm.send(opponent.get_agent(), dest=ai)
    
    # Start coordinator loop
    while True:
        for idx in range(n_agents):
            player = rmleague.get_player(idx)
            opponent, tf = player.get_match()
            for ai in range(actor_lower_bounds[idx], actor_upper_bounds[idx]):
                sub_comms[idx].send(opponent.get_agent(), dest=ai)
  

if __name__ == '__main__':
  main()
  