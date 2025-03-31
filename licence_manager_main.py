from tkinter import Tk
from licence_manager_interface import LicenceManagerFrame

root = Tk()
root.title("Gestion des crédits")
frame = LicenceManagerFrame(master=root)
root.mainloop()
