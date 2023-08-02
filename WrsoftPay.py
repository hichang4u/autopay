# GUI를 위한 PKG
from tkinter import *
from tkinter import filedialog
import tkinter.ttk as ttk
from configparser import ConfigParser
import pandas as pd

# pdf 변환을 위한 PKG
import win32com.client
import os
from PyPDF2 import PdfReader, PdfWriter

# 이메일 전송을 위한 PKG
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#print("work dir = ", os.getcwd())
#print("seperator = ", os.sep)

config = ConfigParser()
#with open('Config/wrsoft.ini', 'r') as configFile:
#    config.read(configFile, encoding='UTF-8')
config.read(os.getcwd() + os.sep + 'Config/wrsoft.ini', encoding='utf-8')

#print(config['DEFAULT']['savefoldername'])
#print(config.get('DEFAULT', 'sourcefilename'))

def WrsoftPay(RFolder, RFile, mTitle, mMain, mYN):
    if mYN == True:
        # 내 메일 정보 가져오기
        #dfmail = pd.read_excel(MData)

        # 메일 필요 정보 초기화하기
        #   세션 생성
        s = smtplib.SMTP('smtp.naver.com', 587)

        #    TLS 보안 시작
        s.starttls()

        #    로그인 인증
        #s.login(dfmail['mailID'][0], dfmail['mailPW'][0])
        s.login(config.get('EMAIL', 'mailid'), config.get('EMAIL', 'mailpw'))

    # 필요 데이터 읽어오기 (pandas)
    dfRaw = pd.read_excel(RFile, sheet_name='Raw')
    #dfMaster = pd.read_excel(RFile, sheet_name='Master')
    dfPrivate = pd.read_excel(RFile, sheet_name='Private')
    dfRaw = dfRaw.merge(dfPrivate, on='사번')

    # None 값 ''으로 대체하기
    dfRaw = dfRaw.fillna('')

    # 필요 데이터 읽어오기 (pywin32, Format)
    excel = win32com.client.Dispatch("Excel.Application")
    # 개발시 True, 배포시 False
    excel.Visible = False

    wbPay = excel.Workbooks.Open(RFile)
    wsFormat = wbPay.Sheets("Format")

    # 저장할 폴더 지정
    FPath = RFolder

    # 인원별 반복문
    for index, row in dfRaw.iterrows():
        # 파일 타이틀 가져오기
        # wsFormat.Cells(2, 3).Value = '2023년 07월 급여명세서'
        wsFormat.Cells(2, 3).Value = txtFT.get()

        # 인적 정보 가져오기
        wsFormat.Cells(4, 5).Value = str(row['생년월일'])
        wsFormat.Cells(5, 5).Value = str(row['사번'])
        wsFormat.Cells(6, 5).Value = str(row['입사일'])
        wsFormat.Cells(4, 9).Value = str(row['이름_x'])
        wsFormat.Cells(5, 9).Value = str(row['직위'])
        wsFormat.Cells(6, 9).Value = str(row['지급일'])

        # 지급 정보 가져오기
        wsFormat.Cells(10, 5).Value = str(row['기본급'])
        wsFormat.Cells(11, 5).Value = str(row['직책수당'])
        wsFormat.Cells(12, 5).Value = str(row['월차수당'])
        wsFormat.Cells(13, 5).Value = str(row['식대'])
        wsFormat.Cells(14, 5).Value = str(row['자가운전보조금'])
        wsFormat.Cells(15, 5).Value = str(row['야간근로수당'])
        wsFormat.Cells(16, 5).Value = str(row['급여소급분'])
        wsFormat.Cells(17, 5).Value = str(row['연장근로수당'])
        wsFormat.Cells(18, 5).Value = str(row['설날상여'])
        wsFormat.Cells(19, 5).Value = str(row['전월미지급'])

        # 공제 정보 가져오기
        wsFormat.Cells(10, 9).Value = str(row['국민연금'])
        wsFormat.Cells(11, 9).Value = str(row['건강보험'])
        wsFormat.Cells(12, 9).Value = str(row['장기요양보험'])
        wsFormat.Cells(13, 9).Value = str(row['고용보험'])
        wsFormat.Cells(14, 9).Value = str(row['건강보험정산'])
        wsFormat.Cells(15, 9).Value = str(row['장기요양보험정산'])
        #   wsFormat.Cells(16, 9).Value = ''
        wsFormat.Cells(17, 9).Value = str(row['소득세'])
        wsFormat.Cells(18, 9).Value = str(row['지방소득세'])
        wsFormat.Cells(19, 9).Value = str(row['농특세'])

        # 근무 내역 가져오기
        wsFormat.Cells(28, 3).Value = str(row['근로일수'])
        wsFormat.Cells(28, 4).Value = str(row['총근로시간수'])
        wsFormat.Cells(28, 5).Value = str(row['연장근로시간수'])
        wsFormat.Cells(28, 6).Value = str(row['야간근로시간수'])
        wsFormat.Cells(28, 7).Value = str(row['휴일근로시간수'])
        wsFormat.Cells(28, 8).Value = str(row['통상시급'])
        wsFormat.Cells(28, 9).Value = str(row['가족수'])
        wsFormat.Cells(28, 10).Value = str(row['비고'])

        # 계산 방법 가져오기
        wsFormat.Cells(31, 9).Value = str(row['기본급'])
        wsFormat.Cells(32, 9).Value = str(row['직책수당'])
        wsFormat.Cells(33, 9).Value = str(row['식대'])
        wsFormat.Cells(34, 9).Value = str(row['자가운전보조금'])
        wsFormat.Cells(35, 9).Value = str(row['국민연금'])
        wsFormat.Cells(36, 9).Value = str(row['건강보험'])
        wsFormat.Cells(37, 9).Value = str(row['장기요양보험'])
        wsFormat.Cells(38, 9).Value = str(row['고용보험'])

        # PDF 파일명 설정
        FName = str(row['사번']) + '_' + str(row['이름_x']) + '.pdf'
        pwdFName = str(row['사번']) + '_' + str(row['이름_x']) + '_pwd.pdf'
        # PDF 파일 저장하기
        wbPay.ExportAsFixedFormat(0, os.path.join(FPath, FName))

        # PDF 파일 암호걸기
        with open(os.path.join(FPath, FName), "rb") as in_file:
            input_pdf = PdfReader(in_file)

            output_pdf = PdfWriter()
            # Add all pages to the writer
            for page in input_pdf.pages:
                output_pdf.add_page(page)

            # Add a password to the new PDF
            output_pdf.encrypt(str(row['pdf-password']))

            with open(os.path.join(FPath, pwdFName), "wb") as out_file:
                output_pdf.write(out_file)

        # 이메일 발송
        if mYN == True:
            msg = MIMEMultipart()
            msg['Subject'] = mTitle
            #msg['From'] = dfmail['mailID'][0]
            msg['From'] = config.get('EMAIL', 'mailid')
            msg['To'] = row['e-mail']
            msg.attach(MIMEText(mMain))

            f = os.path.join(FPath, pwdFName)
            fil = open(f, "rb")

            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
            msg.attach(part)

            # 메일 보내기
            #s.sendmail(dfmail['mailID'][0], row['e-mail'], msg.as_string())
            s.sendmail(config.get('EMAIL', 'mailid'), row['e-mail'], msg.as_string())

    # 엑셀 닫고 종료
    wbPay.Close(False)
    excel.Quit()

    # 이메일 세션 종료
    if mYN == True:
        s.quit()

# 폴더경로 바꾸는 버튼을 눌렀을때 업데이트
def onClick(i):
    folder_selected = filedialog.askdirectory()
    foldName = folder_selected.replace('/','\\')
    lbPath[i].config(text=foldName)
    #df.Detail[i] = foldName
    #writer = pd.ExcelWriter('Master/Master.xlsx', engine='xlsxwriter')
    #df.to_excel(writer, sheet_name='Folder', index=False)
    #dff.to_excel(writer, sheet_name='File', index=False)
    #writer.close()
    config.set('DEFAULT', 'savefolder', foldName)
    with open('Config/wrsoft.ini', 'wt', encoding='utf-8') as configFile:
        config.write(configFile)
    return

# 파일경로와 이름 바꾸는 버튼을 눌렀을때 업데이트
def onClickf(i):
    folder_selected = filedialog.askopenfile()
    fileName = folder_selected.name.replace('/','\\')
    lbPathf[i].config(text=fileName)
    #dff.Detail[i] = fileName
    #writer = pd.ExcelWriter('Master/Master.xlsx', engine='xlsxwriter')
    #df.to_excel(writer, sheet_name='Folder', index=False)
    #dff.to_excel(writer, sheet_name='File', index=False)
    #writer.close()
    config.set('DEFAULT', 'sourcefile', fileName)
    with open('Config/wrsoft.ini', 'wt', encoding='utf-8') as configFile:
        config.write(configFile)
    return

# GUI 구성
win = Tk()
win.geometry("550x360")
win.title('(주)우리소프트 자동 개별 급여명세서 발송기')

# GUI 창의 폴더 / 파일 경로에 대한 정보 엑셀 기준정보 파일에서 가져오기
#df = pd.read_excel("Master/Master.xlsx", sheet_name="Folder")
#dff = pd.read_excel("Master/Master.xlsx", sheet_name="File")

# 폴더 경로 설정 GUI
frame1 = Frame(win, pady=5)
frame1.pack()
lbName = []
lbPath = []
btnPath =[]

#for i in df.index:
lbName.append(Label(frame1, text=config.get('DEFAULT', 'savefoldername'), width=15))
lbName[0].grid(row=0, column=0, sticky=W)
lbPath.append(Label(frame1, text=config.get('DEFAULT', 'savefolder'), width=45, anchor='w'))
lbPath[0].grid(row=0, column=1, sticky=W)
btnPath.append(Button(frame1, text="Change Path", width=10, command=lambda i=0: onClick(i)))
btnPath[0].grid(row=0, column=2, sticky=W)

# 파일 경로 설정 GUI
frame2 = Frame(win, pady=5)
frame2.pack()
lbNamef = []
lbPathf = []
btnPathf =[]

#for i in dff.index:
lbNamef.append(Label(frame2, text=config.get('DEFAULT', 'sourcefilename'), width=15))
lbNamef[0].grid(row=0, column=0, sticky=W)
lbPathf.append(Label(frame2, text=config.get('DEFAULT', 'sourcefile'), width=45, anchor='w'))
lbPathf[0].grid(row=0, column=1, sticky=W)
btnPathf.append(Button(frame2, text="Change Path", width=10, command=lambda i=0: onClickf(i)))
btnPathf[0].grid(row=0, column=2, sticky=W)

# 메일 제목 label
frame3 = Frame(win, pady=5)
frame3.pack()
Label(frame3, text='메일 제목', width=70, anchor='w').pack()

# 메일 제목 TextBox
frame4 = Frame(win)
frame4.pack()
txtMT = Text(frame4, width=70, height=1, padx=5, pady=5)
txtMT.insert(INSERT, '202X년 XX월 급여명세서 송부의 건')
txtMT.pack()

# 메일 본문 label
frame5 = Frame(win, pady=5)
frame5.pack()
Label(frame5, text='메일 본문', width=70,  anchor='w').pack()

# 메일 본문 TextBox
frame6 = Frame(win)
frame6.pack()
txtMM = Text(frame6, width=70, height=5, padx=5, pady=5)
txtMM.insert(INSERT, '202X년 XX월 급여명세서를 첨부파일과 같이 송부드립니다.')
txtMM.pack()

# 파일 타이틀 label
frame7 = Frame(win, pady=5)
frame7.pack()
Label(frame7, text='파일 타이틀', width=70,  anchor='w').pack()

# 파일 타이틀 TextBox
frame8 = Frame(win)
frame8.pack()
txtFT = Entry(frame8, width=70)
txtFT.insert(0, '202X년 XX월 급여명세서')
txtFT.pack()

# 실행 버튼 GUI
frame9 = Frame(win, pady=20)       # Row of buttons
frame9.pack()

# Keywork Change 버튼
btnMF = Button(frame9, text="개별 파일 만들기", width=30,
    command = lambda : WrsoftPay(lbPath[0]['text'], lbPathf[0]['text'], txtMT.get(1.0, END), txtMM.get(1.0, END), False))
btnMF.grid(row=0, column=0, sticky=W)
btnSM = Button(frame9, text="개별 메일 보내기", width=30,
    command = lambda : WrsoftPay(lbPath[0]['text'], lbPathf[0]['text'], txtMT.get(1.0, END), txtMM.get(1.0, END), True))
btnSM.grid(row=0, column=1, sticky=W)

win.mainloop()