from graia.broadcast.utilles import NestableIterable


o = NestableIterable([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

for i in o:
    print("", i)
    if i == 3:
        for ii in o:
            print("    ", ii)
            if ii == 7:
                for iii in o:
                    print("        ", iii)
