# MLFQ scheduler implementation

from collections import deque

class MLFQScheduler:
    def __init__(self, quanta):
        pass

    # called when a job is first created -- the job is assumed
    # to be ready at this point (note: job_ready will not be called
    # for a job's first CPU burst)
    def job_created(self, jid):
        pass

    # called when a job becomes ready after an I/O burst completes
    def job_ready(self, jid):
        pass

    # called when a job's current CPU burst runs to the end of its
    # allotted time quantum without completing -- the job is
    # still in the ready state
    def job_quantum_expired(self, jid):
        pass
    
    # called when a job is preempted mid-quantum due to our
    # returning True to `needs_resched` -- the job is still in
    # the ready state
    def job_preempted(self, jid):
        pass

    # called after a job completes its final CPU burst -- the job
    # will never become ready again
    def job_terminated(self, jid):
        pass

    # called when a job completes its CPU burst within the current
    # time quantum and has moved into its I/O burst -- the job is
    # currently blocked
    def job_blocked(self, jid):
        pass

    # called by the simulator after new jobs have been made ready.
    # we should return True here if we have a more deserving job and
    # want the current job to be preempted; otherwise return False
    def needs_resched(self):
        return False

    # return a two-tuple containing the job ID and time quantum for
    # the next job to be scheduled; if there is no ready job,
    # return (None, 0)
    def next_job_and_quantum(self):
        return (None, 0)

    # called by the simulator after all jobs have terminated -- we
    # should at this point compute and print out well-formatted
    # scheduler statistics
    def print_report(self):
        pass

