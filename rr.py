from collections import deque

class RoundRobinScheduler:
    def __init__(self, quantum=3):
        self.quantum = quantum
        self.ready_queue = deque()   # internal wait queue

    def job_created(self, jid):
        self.ready_queue.append(jid)

    def job_ready(self, jid):
        self.ready_queue.append(jid)
    
    def job_preempted(self, jid):
        self.ready_queue.append(jid)

    def job_terminated(self, jid):
        pass

    def job_blocked(self, jid):
        pass

    def next_job_and_quantum(self):
        return (self.ready_queue.popleft() if self.ready_queue else None,
                self.quantum)
