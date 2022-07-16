"""
分割大文件pdf
"""

import PyPDF2
import os


def get_file_size(file_path, dround=3):
    return round(os.path.getsize(file_path) / 1024 / 1024, dround)


def get_pdf_info(file_path):
    pdfFile = open(file_path, 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFile, strict=False)
    total_pages = pdfReader.numPages
    size = get_file_size(file_path)
    return total_pages, size


def extract_pdf(origFileName, newFileName, page=None, nums=1, rotation=0):
    pdfFile = open(origFileName, 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFile, strict=False)
    pdfWriter = PyPDF2.PdfFileWriter()

    assert page is not None, '请指定页数page!'
    page = int(page)
    for p in range(page, page + nums):
        pageObj = pdfReader.getPage(p)
        pageObj.rotateClockwise(rotation)
        pdfWriter.addPage(pageObj)

    newFile = open(newFileName, 'wb')
    pdfWriter.write(newFile)

    pdfFile.close()
    newFile.close()


def main():
    origFileName = 'p1.pdf'
    rotation = 0
    page = 1
    nums = 1
    newFileName = f'page_{page}_to_{page + nums - 1}.pdf'

    extract_pdf(origFileName, newFileName, page=page, nums=nums, rotation=rotation)


if __name__ == "__main__":
    import os
    os.chdir('myutils')
    main()