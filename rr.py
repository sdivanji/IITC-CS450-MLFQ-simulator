# Sample round robin scheduler implementaion
# Michael Lee <lee@iit.edu>

from __future__ import print_function
from collections import deque

class RoundRobinScheduler:
    def __init__(self, quantum=3):
        self.quantum = quantum
        self.ready_queue = deque()   # internal wait queue
        self.preempt_cnts   = dict()
        self.queue_lengths = []

    def job_created(self, jid):
        self.ready_queue.append(jid)
        self.preempt_cnts[jid] = 0

    def job_ready(self, jid):
        self.queue_lengths.append(len(self.ready_queue))
        self.ready_queue.append(jid)

    def job_quantum_expired(self, jid):
        self.queue_lengths.append(len(self.ready_queue))
        self.ready_queue.append(jid)
        self.preempt_cnts[jid] += 1
    
    def job_preempted(self, jid):
        self.queue_lengths.append(len(self.ready_queue))
        self.ready_queue.appendleft(jid)
        self.preempt_cnts[jid] += 1

    def job_terminated(self, jid):
        pass

    def job_blocked(self, jid):
        pass

    def needs_resched(self):
        return False

    def next_job_and_quantum(self):
        return (self.ready_queue.popleft() if self.ready_queue else None,
                self.quantum)
    
    def print_report(self):
        print()
        print('  JID | # Preempts')
        print('------------------')
        for jid in sorted(self.preempt_cnts.keys()):
            print('{:5d} | {:10d}'.format(jid, self.preempt_cnts[jid]))
        print()

        avg_q_len = sum(self.queue_lengths, 0.0) / len(self.queue_lengths)
        print("Avg queue length = {:.2f}".format(avg_q_len))
        print("Max queue length = {:.2f}".format(max(self.queue_lengths)))
        print()
