```
=== Block: ConfirmationPDF ===
Public: False
Flow: PDF
Inputs: RequestId:LoanRequest Identifier (mandatory)
Events: OnReady(IsReady:Boolean), ReturnBinary(File:Binary Data, FileName:Text)
StyleSheet: (see below)

--- STYLESHEET ---
.pdf-logo { height: 100px; width: 100px; }
.pdf-content { width: 730px; margin: 34px auto; color: #000000; line-height: 1.8; }
@media print { html, body { height: initial !important; overflow: initial !important; -webkit-print-color-adjust: exact; line-height: 1.8; } }

--- WIDGETS ---
[1] If (unnamed)
  [TRUE BRANCH]
    [1.T.1] Container 'Container'
      [1.T.1.1] Container 'PDFContent'
        [1.T.1.1.1] Container 'BasicLoanInformation'
          [1.T.1.1.1.1] Text 'Text'
        [1.T.1.1.2] Container 'LoanInformation'
        [1.T.1.1.3] Container 'Footer'
          [1.T.1.1.3.1] Expression 'Expression'
  [FALSE BRANCH]
```
