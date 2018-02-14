# -*- coding: utf-8 -*-


from TM1py.Objects.TM1Object import TM1Object


class Application(TM1Object):

    def __init__(self, path, content):
        self.path = path
        self.content = content

    def to_xlsx(self, path_to_file):
        with open(path_to_file, "wb") as file:
            file.write(self.content)
