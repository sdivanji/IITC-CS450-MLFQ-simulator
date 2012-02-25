# CS 450 scheduling simulation assignment driver program
#
# - run with `python sched_sim.py -h` for command line help
#  
# Michael Lee <lee@iit.edu>

from __future__ import print_function
import io
import logging
import argparse
import rr
import mlfq
from collections import deque

class Job:
    # possible job states
    RUNNING    = 0
    READY      = 1
    BLOCKED    = 2
    TERMINATED = 3
    
    state_names = ['Running',
                   'Ready',
                   'Blocked',
                   'Terminated']

    def __init__(self, jid):
        self.jid = jid
        self.state = Job.READY

        # upcoming CPU and IO bursts
        self.bursts = None

        # dynamic process info updated by simulator
        self.wait_time      = 0
        self.completed_ts   = 0
        self.last_ready_ts  = 0
        self.pending_event  = None  # at most 1 pending event per job

        # "baseline stats" -- we compute these before simulating
        self.arrival_ts     = 0
        self.n_bursts       = 0
        self.run_time       = 0
        self.io_time        = 0

    def __repr__(self):
        return ('[ job {} ; burst len = {}, total wait = {} ]').format(
                self.jid,
                self.bursts[0],
                self.wait_time)


class Event:
    # possible (scheduled) events
    JOB_ARRIVED         = 0
    CPU_BURST_COMPLETED = 1
    IO_BURST_COMPLETED  = 2
    QUANTUM_COMPLETED   = 3
    NONE                = 4

    event_names = ['Arrival',
                   'CPU burst complete',
                   'IO burst complete',
                   'Preempted']
    
    def __init__(self, job, event_type):
        self.job = job
        self.event_type = event_type

    def __repr__(self):
        return 'Job {}; {}'.format(self.job.jid,
                                  Event.event_names[self.event_type])


class Simulator:
    def __init__(self, initfilename, scheduler):
        self.jobs = dict()
        self.events = dict()
        self.scheduler = scheduler
        with open(initfilename) as initfile:
            numjobs = int(initfile.readline())
            for i in range(numjobs):
                vals = initfile.readline().split()
                jid = int(vals[0])
                job = self.jobs[jid] = Job(jid)
                job.arrival_ts = int(vals[1])
                job.n_bursts = int(vals[2])
                self.schedule_event(job, job.arrival_ts, Event.JOB_ARRIVED)
                job.bursts = deque(map(int, vals[3:]))
                self.fill_baseline_stats(job)

    def fill_baseline_stats(self, job):
        for i, b in enumerate(job.bursts):
            if i%2 == 0:
                job.run_time += b
            else:
                job.io_time += b

    def schedule_event(self, job, time, event_type):
        event = Event(job, event_type)
        event_list = self.events.get(time, [])
        event_list.append(event)
        self.events[time] = event_list
        job.pending_event = event

    def cancel_event_for(self, job):
        if job.pending_event:
            job.pending_event.event_type = Event.NONE

    def do_sim(self, max_time=50000):
        self.current_job = None
        self.num_completed = 0
        time = 0
        while time <= max_time and self.num_completed < len(self.jobs):
            if self.events.get(time):
                logging.info('Time %d', time)
            if self.current_job:
                self.current_job.bursts[0] -= 1
                assert self.current_job.bursts[0] >= 0
            events = self.events.get(time, [])
            if events:
                self._process_events(events, time)
            if not self.current_job:
                self._run_new_job(time)
            elif self.scheduler.needs_resched():
                logging.info(' - Preempting %s', self.current_job)
                self.current_job.state = Job.READY
                self.current_job.last_ready_ts = time
                self.scheduler.job_preempted(self.current_job.jid)
                self.cancel_event_for(self.current_job)
                self.current_job = None
                self._run_new_job(time)
            time += 1
    
    # Deliver and process all events that happen at time=now, notifying
    # the scheduler and updating job state.
    def _process_events(self, events, now):
        for e in events:
            if e.event_type == Event.JOB_ARRIVED:
                logging.info(' - Arrival of %s', e.job)
                e.job.state = Job.READY
                e.job.last_ready_ts = now
                self.scheduler.job_created(e.job.jid)
            elif e.event_type == Event.CPU_BURST_COMPLETED:
                e.job.bursts.popleft()
                if e.job.bursts:
                    logging.info(' - Job %d CPU burst complete', e.job.jid)
                    logging.info(' - Blocking job %d for %d', 
                                 e.job.jid, e.job.bursts[0])
                    e.job.state = Job.BLOCKED  # CPU done, proceed to IO burst
                    io_len = e.job.bursts.popleft()
                    self.schedule_event(e.job, now+io_len, 
                                        Event.IO_BURST_COMPLETED)
                    self.scheduler.job_blocked(e.job.jid)
                else:
                    logging.info(' - Job %d terminated', e.job.jid)
                    e.job.state = Job.TERMINATED
                    e.job.completed_ts = now
                    self.scheduler.job_terminated(e.job.jid)
                    self.num_completed += 1
                self.current_job = None
            elif e.event_type == Event.QUANTUM_COMPLETED:
                logging.info(' - Job %d quantum expired', e.job.jid)
                e.job.state = Job.READY
                e.job.last_ready_ts = now
                self.scheduler.job_quantum_expired(e.job.jid)
                self.current_job = None
            elif e.event_type == Event.IO_BURST_COMPLETED:
                logging.info(' - Job %d completed I/O', e.job.jid)
                e.job.state = Job.READY  # IO done, proceed to CPU burst
                e.job.last_ready_ts = now
                self.scheduler.job_ready(e.job.jid)
    
    # Tries to retrieve a new job from the scheduler and run it. If successful,
    # arrange for a future event where it either completes its CPU burst or its
    # time quantum expires
    def _run_new_job(self, now):
        (jid, quantum) = self.scheduler.next_job_and_quantum()
        if jid is None:
            return
        job = self.jobs[jid]
        assert job.state == Job.READY, \
               "Can't schedule JID={}, state={}".format(job.jid,
                                                        Job.state_names[job.state])
        job.state = Job.RUNNING
        job.wait_time += now - job.last_ready_ts
        logging.info(' - Scheduling %s with q=%d', job, quantum)
        if job.bursts[0] <= quantum:
            self.schedule_event(job,
                                now + job.bursts[0],
                                Event.CPU_BURST_COMPLETED)
        else:
            self.schedule_event(job,
                                now + quantum,
                                Event.QUANTUM_COMPLETED)
        self.current_job = job

    def print_report(self):
        print()
        print('{:>5s} | {:>10s} | {:>10s} | {:>10s} | {:>10s}'.format(
                'JID', 'Avg CPU', 'Avg wait', 'Avg rspnse', 'Turnaround'))
        print('-' * 57)
        sum_cpu = sum_wait = sum_rsp = sum_trn = 0
        for jid in sorted(self.jobs):
            job = self.jobs[jid]
            if job.state != Job.TERMINATED:
                print('Job', jid, 'didn\'t complete.',
                      'Consider increasing simulation time.')
                continue
            n_cpubursts = float(job.n_bursts//2 + 1)
            avg_cpu  = job.run_time / n_cpubursts
            sum_cpu  += avg_cpu
            avg_wait = job.wait_time / n_cpubursts
            sum_wait += avg_wait
            avg_rsp  = avg_cpu + avg_wait
            sum_rsp  += avg_rsp
            trnarnd  = job.completed_ts - job.arrival_ts
            sum_trn  += trnarnd
            print('{:5d} | {:10.2f} | {:10.2f} | {:10.2f} | {:10d}'.format(
                    jid, avg_cpu, avg_wait, avg_rsp, trnarnd))
        print('-' * 57)
        print('  Avg | {:10.2f} | {:10.2f} | {:10.2f} | {:10.2f}'.format(
                sum_cpu / len(self.jobs),
                sum_wait / len(self.jobs),
                sum_rsp / len(self.jobs),
                float(sum_trn) / len(self.jobs)))
        print()
        self.scheduler.print_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CPU scheduling simulator')
    parser.add_argument('--conf', '-c',
                        default='jobs.conf',
                        help='configuration file name',
                        metavar='filename')

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='verbose output')

    parser.add_argument('--sched', '-s',
                        default='rr',
                        choices=['rr', 'mlfq'],
                        help="scheduling algorithm ('rr' or 'mlfq')",
                        metavar='alg')

    parser.add_argument('--maxtime', '-m',
                        type=int,
                        default=50000,
                        help='max simulation time',
                        metavar='time')

    parser.add_argument('--quanta', '-q',
                        default=[5],
                        type=int,
                        nargs='+',
                        help='time quantum/a for scheduler (specify > 1 for mlfq)',
                        metavar='Q')
                        
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    if args.sched == 'rr':
        scheduler = rr.RoundRobinScheduler(args.quanta[0])
    else:
        scheduler = mlfq.MLFQScheduler(args.quanta)
    
    sim = Simulator(args.conf, scheduler)
    sim.do_sim(args.maxtime)
    sim.print_report()
