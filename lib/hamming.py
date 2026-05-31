

def decodeHamming(normalized, parityPositions):
    '''
    Takes data as input
    Applies single error fix 
    If data passes filter, set message to it.
    Using hamming(15,11) noise filtering. Includes 4 parity bits which can fix 1 bit errors
    '''
    # hamming15 = [0 if x < cutOffLine else 1 for x in gData] # Normalize to 0 and 1
    # See if any errors
    syndrome = 0
    for p in sorted(parityPositions): # {1, 2, 4, 8} 
        covered = []
        for pos in range(1, 16):      # pos = 1, 2, 3, ... 15
            if pos & p:                # anding check if the number is covered by the parity bit. 0 0 0 0 each digit has a master
                covered.append(normalized[pos - 1])  # grab the bit value at that position
        result = 0
        for bit in covered: # or everything to see if any problems.
            result = result ^ bit
        if result != 0: #if problems, add to syndrome
            syndrome += p

    else:
        # Unfixable
        if syndrome > 15:
            print("SYNDROME OB")

        # Single error fix
        elif syndrome != 0:
            corrected = normalized
            corrected[syndrome - 1] ^= 1
            return corrected

        # All good
        else:
            return normalized

def encodeHamming(data, dataPositions, parityPositions): 
    '''
    Turn 11 data bits into 15 bit hamming code.
    Includes 4 parity bits capable of repairing 1 error.
    '''
    product = [0] * 15
    for i, pos in enumerate(dataPositions): # Sets data bits into correct positions
        product[pos - 1] = data[i]

    for p in sorted(parityPositions):  # Go through each of the parity bit positions
        covered = []
        for pos in range(1, 16):        # pos = 1, 2, 3, ... 15
            if pos != p:                # skip the parity bit itself
                if pos & p:             # anding check if the number is covered by the parity bit. 0 0 0 0 each digit has a master
                    covered.append(product[pos - 1])
        result = 0
        for bit in covered:
            result = result ^ bit       # XOR everything together
        product[p - 1] = result        # set the parity bit to the result

    return product