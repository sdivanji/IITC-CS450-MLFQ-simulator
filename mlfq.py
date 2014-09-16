# MLFQ scheduler implementation

from collections import deque

class RRQueue:
    def __init__(self, quantum=3):
        self.quantum = quantum
        self.readyQueue = deque()
        self.active = None
        self.queueLengths = []
    
    def hasJobs(self):
        return len(self.readyQueue)>0 or self.active!=None

class Job:
    READY = 0
    RUNNING = 1
    BLOCKED = 2
    DONE = 3
    def __init__(self, jid):
        self.jid = jid
        self.state = Job.READY
        self.queueID = 0 #jobs always start in the "high-priority" queue! Queue 0 is the highest priority and queue 4 is tje lowest priority.
        self.preempt_cnts = 0
        self.quantumExpired = False #applies over ONE BURST



class MLFQScheduler:
    
    UNDERFLOW_THRESHHOLD = 20
    OVERFLOW_THRESHHOLD = 20
    USE_EXPANSION = True
    
    def __init__(self, quanta):
        self.jobsByJid = dict()
        self.queueArray = [None] * len(quanta)
        for i in range(0, len(quanta)):
            self.queueArray[i] = RRQueue(quanta[i]) # Since each queue implements a RR with a fixed q
        self.activeQueueID = 0
        self.resched = False
        self.currentUnderflow = 0
        self.currentOverflow = 0
    
    
    # called when a job is first created -- the job is assumed
    # to be ready at this point (note: job_ready will not be called
    # for a job's first CPU burst)
    def job_created(self, jid):
        newjob = Job(jid)
        self.jobsByJid[jid] = newjob
        self.queueArray[0].readyQueue.appendleft(newjob)
    
    # called when a job becomes ready after an I/O burst completes
    def job_ready(self, jid):
        readyjob = self.jobsByJid[jid]
        readyjob.state = Job.READY
        readyJobQ = self.queueArray[readyjob.queueID]
        self.log_queue_lengths()
        readyJobQ.readyQueue.appendleft(readyjob)
    
    # called when a job's current CPU burst runs to the end of its
    # allotted time quantum without completing -- the job is
    # still in the ready state
    def job_quantum_expired(self, jid):
        expjob = self.jobsByJid[jid]
        expjobQueue = self.queueArray[expjob.queueID]
        assert expjob==expjobQueue.active
        expjobQueue.active = None
        if expjob.queueID<(len(self.queueArray)-1):
            expjob.queueID += 1
            expjobQueue = self.queueArray[expjob.queueID]
        elif MLFQScheduler.USE_EXPANSION: #we're in the lowest priority queue, and expansions are on
            self.currentOverflow+=1
            if self.currentOverflow>MLFQScheduler.OVERFLOW_THRESHHOLD:
                #make a new low-priority queue, and move the job into it
                self.queueArray.append(RRQueue(self.queueArray[len(self.queueArray)-1].quantum * 2))
                expjob.queueID += 1
                expjobQueue = self.queueArray[expjob.queueID]
        self.log_queue_lengths()
        expjob.state = Job.READY
        expjob.preempt_cnts += 1
        expjob.quantumExpired = True
        expjobQueue.readyQueue.appendleft(expjob)
    
    
    # called when a job is preempted mid-quantum due to our
    # returning True to `needs_resched` -- the job is still in
    # the ready state
    def job_preempted(self, jid):
        prejob = self.jobsByJid[jid]
        prejobQ = self.queueArray[prejob.queueID]
        self.log_queue_lengths()
        assert prejob==prejobQ.active
        prejobQ.active = None
        prejobQ.readyQueue.appendleft(prejob)
        prejob.preempt_cnts += 1
    
    # called after a job completes its final CPU burst -- the job
    # will never become ready again
    def job_terminated(self, jid):
        termjob = self.jobsByJid[jid]
        termjobQ = self.queueArray[termjob.queueID]
        assert termjob==termjobQ.active
        termjobQ.active = None
        termjob.state = Job.DONE
    
    # called when a job completes its CPU burst within the current
    # time quantum and has moved into its I/O burst -- the job is
    # currently blocked
    def job_blocked(self, jid):
        blockjob = self.jobsByJid[jid]
        blockjobQ = self.queueArray[blockjob.queueID]
        assert blockjob == blockjobQ.active
        blockjobQ.active = None
        if (not blockjob.quantumExpired):
            if blockjob.queueID > 0:
                blockjob.queueID -= 1
                blockjobQ = self.queueArray[blockjob.queueID]
            elif MLFQScheduler.USE_EXPANSION:
        #we're in the highest-priority queue, and expansions are on
        
        
            	blockjob.state = Job.BLOCKED
            	blockjob.quantumExpired = False
    
    # called by the simulator after new jobs have been made ready.
    # we should return True here if we have a more deserving job and
    # want the current job to be preempted; otherwise return False
    def needs_resched(self):
        if (self.activeQueueID == 0):
            resched = False
            return False
        
        for i in range(0, self.activeQueueID):
            if (len(self.queueArray[i].readyQueue) > 0):
                resched = True
                return resched
        
        resched=False
        return resched
    
    # return a two-tuple containing the job ID and time quantum for
    # the next job to be scheduled; if there is no ready job,
    # return (None, 0)
    def next_job_and_quantum(self):
        selectQ = self.queueArray[self.activeQueueID]
        assert selectQ.active == None
        selectQID = 0
        selectQ = self.queueArray[self.activeQueueID]
        
        while (selectQID<len(self.queueArray)) and (not self.queueArray[selectQID].hasJobs()):
            selectQID+=1
        #we've been through EVERYTHING, and found no jobs
        if selectQID==len(self.queueArray):
            return (None, 0)
        
        selectQ = self.queueArray[selectQID]
        activejob = selectQ.readyQueue.pop()
        selectQ.active = activejob
        activejob.state = Job.RUNNING
        return (activejob.jid, selectQ.quantum)
    
    # called by the simulator after all jobs have terminated -- we
    # should at this point compute and print out well-formatted
    # scheduler statistics
    def print_report(self):
        print('')
        print('  JID | # Preempts')
        print('------------------')
        for jid in sorted(self.jobsByJid.keys()):
            job = self.jobsByJid[jid]
            print('{:5d} | {:10d}'.format(jid, job.preempt_cnts))
        print('')
        print('')
        
        print("Queue # | Average Length | Max Length")
        print("-------------------------------------")
        for qid in range(0,len(self.queueArray)):
            queue = self.queueArray[qid]
            avg_q_len = sum(queue.queueLengths, 0.0) / len(queue.queueLengths)
            print('{:7d} | {:14.2f} | {:10.2f}').format(qid, avg_q_len, max(queue.queueLengths))
        pass
    
    
    def log_queue_lengths(self):
        for i in range(0,len(self.queueArray)):
            logQ = self.queueArray[i]
            logQ.queueLengths.append(len(logQ.readyQueue))
