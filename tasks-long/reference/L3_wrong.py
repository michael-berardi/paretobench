# a shared module is added but the four copies stay
from _ref import *

write("core/skus.py", read("store/skus.py"))
