from tkinter import *
from tkinter import filedialog
from tkinter import font
import pandas as pd

# 폴더 단위의 경로 변경 버튼 클릭시 동작
def onClick(i):
    folder_selected = filedialog.askdirectory()
    lbPath[i].config(text=folder_selected)
    df.Detail[i] = folder_selected
    writer = pd.ExcelWriter('C:/wrsoft/payment/Master.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Folder', index=False)
    dff.to_excel(writer, sheet_name='File', index=False)
    writer.save()

    return

# 파일 단위의 경로 변경 버튼 클릭시 동작
def onClickf(i):
    folder_selected = filedialog.askopenfile()
    lbPathf[i].config(text=folder_selected.name)
    dff.Detail[i] = folder_selected.name
    writer = pd.ExcelWriter('C:/wrsoft/payment/Master.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Folder', index=False)
    dff.to_excel(writer, sheet_name='File', index=False)
    writer.save()
    return

# GUI 창 열기
win = Tk()
win.geometry("550x310")
win.title('자동 개별 급여 명세표 발급기')

# GUI 창의 폴더 / 파일 경로에 대한 정보 엑셀 기준정보 파일에서 가져오기
df = pd.read_excel("C:/wrsoft/payment/Master.xlsx", sheet_name="Folder")
dff = pd.read_excel("C:/wrsoft/payment/Master.xlsx", sheet_name="File")

# frame1 (폴더 경로에 대한 지정) 구성하기
frame1 = Frame(win, pady = 5)
frame1.pack()
lbName = []
lbPath = []
btnPath =[]

for i in df.index:
    lbName.append(Label(frame1, text=df.Item[i], width=15))
    lbName[i].grid(row=i, column=0, sticky=W)
    lbPath.append(Label(frame1, text=df.Detail[i], width=45, anchor = 'w'))
    lbPath[i].grid(row=i, column=1, sticky=W)
    btnPath.append(Button(frame1, text="Change Path", width=10,command=lambda i=i: onClick(i)))
    btnPath[i].grid(row=i, column=2, sticky=W)

# frame2 (특별히 사용되는 파일의 경로에 대한 지정) 구성하기
frame2 = Frame(win, pady = 5)
frame2.pack()
lbNamef = []
lbPathf = []
btnPathf =[]

for i in dff.index:
    lbNamef.append(Label(frame2, text=dff.Item[i], width=15))
    lbNamef[i].grid(row=i, column=0, sticky=W)
    lbPathf.append(Label(frame2, text=dff.Detail[i], width=45, anchor='w'))
    lbPathf[i].grid(row=i, column=1, sticky=W)
    btnPathf.append(Button(frame2, text="Change Path", width=10, command=lambda i=i: onClickf(i)))
    btnPathf[i].grid(row=i, column=2, sticky=W)

# frame3 메일 제목 label
frame3 = Frame(win, pady=5)
frame3.pack()
Label(frame3, text='메일 제목', width=70, anchor='w').pack()

# frame4 메일 제목 TextBox
frame4 = Frame(win)
frame4.pack()
textMT = Text(frame4, width=70, height=1, pady=5, padx=5)
textMT.insert(INSERT, "xx월 급여 내역 송부의 건")
textMT.pack()

# frame5 메일 본문 label
frame5 = Frame(win, pady=5)
frame5.pack()
Label(frame5, text='메일 본문', width=70,  anchor='w').pack()

# frame6 메일 본문 TextBox
frame6 = Frame(win)
frame6.pack()
textMM = Text(frame6, width=70, height=5, pady=5, padx=5)
textMM.insert(INSERT, "xx월 급여 내역을 유첨 파일과 같이 송부드립니다.")
textMM.pack()

# frame7 기능 버튼에 대한 부분 구성하기
frame7 = Frame(win, pady=10)       # Row of buttons
frame7.pack()
# Keywork Change 버튼
btnMF = Button(frame7,text="개별 파일 만들기", width=20)
btnMF.grid(row=0, column=1, sticky=W)
btnSM = Button(frame7, text="개별 메일 송부하기", width=20)
btnSM.grid(row=0, column=2, sticky=W)

win.mainloop()