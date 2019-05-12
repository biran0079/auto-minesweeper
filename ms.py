import win32gui, win32ui, win32con, win32api
from PIL import Image, ImageGrab
import os,math,time,sys
from ctypes import windll
import numpy as np
import random


wh = win32gui.FindWindow(None, '扫雷')
if not wh:
    print("game not open")
    exit(-1)

dch = win32gui.GetWindowDC(wh)
paddingX = 5
paddingY = 2
step = 1

def getBitmap(f):
    data = Image.open(f).load()
    res = []
    for x in range(paddingX, cellSize-paddingX, step):
        for y in range(paddingY, cellSize-paddingY, step):
            res.append(np.array(data[x,y]))
    return np.hstack(res)

left, top, right, bottom = 200, 136, 1734, 960
width = right - left + 1
height = bottom - top + 1
row = 16
col = 30
cellSize = 51
digits = {'1', '2', '3', '4', '5', '6'}

bitmaps = {
    f[:-4] : getBitmap(f) for f in os.listdir() if f.endswith('png')
}

def getCellTopLeftPos(i, j):
    return left + j * cellSize + j // 4, top + i * cellSize + i // 4

def getColor(x,y, screen):
    b = 4 * (y * width + x)
    return screen[b+2:b-1:-1]

def distance(a,b):
    return np.sum(np.square(a-b))

def getCellType(i, j, screen):
    x0,y0 = getCellTopLeftPos(i,j)
    x0 -= left
    y0 -= top
    f=[]
    for x in range(x0+paddingX, x0+cellSize-paddingX, step):
        for y in range(y0+paddingY, y0+cellSize-paddingY, step):
            f.append(getColor(x, y, screen))
    f = np.hstack(f)
    min = 1e100
    res = None
    for k,v in bitmaps.items():
        d = distance(f, v)
        if d < min:
            min = d
            res = k
    if res[0] == '-':
        res = '-'
    if res[0] == 'f':
        res = 'f'
    if '-' in res:
        res = res[0]
    return res

def saveImage(i, j, name):
    img = Image.new('RGB', (cellSize, cellSize))
    data = img.load()
    x0,y0=getCellTopLeftPos(i,j)
    x0-=left
    y0-=top
    screen = getScreenBitmap()
    for x in range(cellSize):
        for y in range(cellSize):
            data[x,y] = tuple(getColor(x0+x, y0+y, screen))
    img.save(name + '.png')

def click(i, j, left=False, right=False):
    x,y = getCellTopLeftPos(i,j)
    x += cellSize // 2
    y += cellSize // 2
    print("clicking {} {}".format(x,y))
    windll.user32.SetCursorPos(x, y)
    time.sleep(0.05)
    downFlag = 0
    upFlag = 0
    if right:
        downFlag += win32con.MOUSEEVENTF_RIGHTDOWN
        upFlag += win32con.MOUSEEVENTF_RIGHTUP
    if left:
        downFlag += win32con.MOUSEEVENTF_LEFTDOWN
        upFlag += win32con.MOUSEEVENTF_LEFTUP
    win32api.mouse_event(downFlag, 0, 0, 0, 0)
    win32api.mouse_event(upFlag, 0, 0, 0, 0)

def getScreenBitmap():
    hwindc = win32gui.GetWindowDC(wh)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, width, height)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
    t=bmp.GetBitmapBits()
    t=[x if x >= 0 else 256 + x for x in t]
    return np.array(t)
    res=[]
    for i in range(height):
        l=[]
        for j in range(width):
            b = 4 * (i * width + j)
            l.append(np.array([t[b+2],t[b+1],t[b]]))
        res.append(l)
    return res

def done(board):
    for i in range(row):
        for j in range(col):
            if board[i][j] == '-':
                return False
    return True

def getBoard():
    print('capturing board..')
    board = []
    screen = getScreenBitmap()
    for i in range(row):
        l=[]
        for j in range(col):
            l.append(getCellType(i,j, screen))
        board.append(l)
    printBoard(board)
    return board

def dfs(board, i, j, vis, screen):
    if (i,j) in vis: return
    vis.add((i,j))
    board[i][j] = getCellType(i,j, screen)
    if board[i][j] == '-': return
    for p in getNeighbor(board, i, j, '-'):
        dfs(board, p[0], p[1], vis, screen)

def explore(board, i, j, screen):
    dfs(board, i, j, set(), screen)

def getNeighbor(board, i, j, c):
    return _getNeightBor(board, i, j, lambda x: x == c)

def getDigitNeighbor(board, i, j):
    return _getNeightBor(board, i, j, lambda x: x in digits)

def _getNeightBor(board, i, j, f):
    res = []
    for d in [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]:
        ti = i + d[0]
        tj = j + d[1]
        if ti >= 0 and ti < row and tj >= 0 and tj < col and f(board[ti][tj]):
            res.append((ti, tj))
    return res

def randomUnknownCell(board):
    res = []
    for i in range(row):
        for j in range(col):
            if board[i][j] == '-':
                res.append((i,j))
    return random.sample(res, 1)[0]

def printBoard(board):
    print("\n".join([" ".join(r) for r in board]))

def getAllCombination(n, k):
    res=[]
    pending=[]
    def helper(i):
        if len(pending) == k:
            res.append(list(pending))
            return
        if i >= n:
            return
        if n - i > k - len(pending):
            helper(i + 1)
        pending.append(i)
        helper(i + 1)
        pending.pop()
    helper(0)
    return res

def contradiction(board, unknowns):
    toCheck = set()
    for p in unknowns:
        c = board[p[0]][p[1]]
        toCheck |= set(getDigitNeighbor(board, p[0], p[1]))
    for p in toCheck:
        flags = getNeighbor(board, p[0], p[1], 'f')
        unknowns = getNeighbor(board, p[0], p[1], '-')
        mineCount = int(board[p[0]][p[1]])
        if len(flags) > mineCount or len(flags) + len(unknowns) < mineCount:
            return True
    return False

def inductionOnUnknowns(board, unknowns, mines):
    cands = []
    for idx in getAllCombination(len(unknowns), mines):
        for k in range(len(unknowns)):
            p = unknowns[k]
            if k in idx:
                board[p[0]][p[1]] = 'f' # temporarily mark as flag
            else:
                 board[p[0]][p[1]] = '0' # place holder to skip inspection
        if not contradiction(board, unknowns):
            cands.append(idx)
        for p in unknowns:
            board[p[0]][p[1]] = '-'
    res = set()
    for k in range(len(unknowns)):
        # if i is in all candidates, then it is a mine
        # if i is in none of candidates, then it is not a mine
        t = [k in cand for cand in cands]
        if all(t):
            res.add((unknowns[k], False, True))
        if not any(t):
            res.add((unknowns[k], True, False))
    return res

def induction(board):
    res = set()
    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] in digits:
                flags = getNeighbor(board, i, j, 'f')
                unknowns = getNeighbor(board, i, j, '-')
                if unknowns:
                    res |= inductionOnUnknowns(board, unknowns, int(board[i][j]) - len(flags))
    return res

def finalPhaseInduction(board):
    flags=0
    unknowns=[]
    for i in range(row):
        for j in range(col):
            if board[i][j] == 'f':
                flags+=1
            elif board[i][j] == '-':
                unknowns.append((i,j))
    if len(unknowns) > 10:
        return set()
    return inductionOnUnknowns(board, unknowns, 99 - flags)

def findMoves(board):
    res = induction(board)
    if not res:
        res = finalPhaseInduction(board)
        if not res:
            res = {
                (randomUnknownCell(board), True, False),
            }
    return res


def play():
    win32gui.ShowWindow(wh, win32con.SW_SHOWMAXIMIZED)
    win32gui.SetForegroundWindow(wh)
    board = getBoard()
    while not done(board):
        moves = findMoves(board)
        for p, left, right in moves:
            click(p[0], p[1], left=left, right=right)
            time.sleep(0.1)
        time.sleep(0.2)
        screen = getScreenBitmap()
        for p,_,_ in moves:
            explore(board, p[0], p[1], screen)
        printBoard(board)

play()
#print(getCellType(1,1, getScreenBitmap()))
#getBoard()
#saveImage(9, 19, '0-2')
#print(induction(getBoard()))
