

class TM1Object:
    """ Parent Class for all TM1 Objects e.g. Cube, Process, Dimension.
    
    """
    def __str__(self):
        return self.body

    def __repr__(self):
        return "{}:{}".format(self.__class__.__name__, self.body)
