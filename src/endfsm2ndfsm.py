from reg2endfsm import *
import queue
def endfsm2ndfsm(endfsm):
    for node in endfsm:
        node.stop = False
        node.seen = 0
    endfsm[-1].stop = True
    counter = 0
    for root in endfsm:
        counter += 1
        q = queue.Queue()
        q.put(root)
        while not q.empty():
            cur = q.get_nowait()
            for nxt in cur.next['']:
                if nxt not in root.next['']:
                    root.next[''].append(nxt)
                if counter != nxt.seen:
                    q.put(nxt)
                if nxt.stop:
                    root.stop = True
            cur.seen = counter
    # for root in endfsm:
    #     for node in root.next['']:
    #         for label, 

