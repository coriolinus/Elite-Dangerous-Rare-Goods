# Elite Dangerous Rare Goods Calculator

Plan your rare goods trade routes with this utility!

## Examples
### How many goods match your criteria?

    > python .\edrg.py --count --filter "Goods.expected_value > 5000" --filter "Station.dist < 5000"
    47

or

    > python .\edrg.py --count --filter "Goods.expected_value > 8000" --filter "Station.dist < 1000"
    24

### Show the best of them:

    > python .\edrg.py --filter "Station.dist < 1000" --display --limit 5 --sort "Goods.expected_value"
    Az Cancri Formula 42 (Fisher Station, AZ Cancri): 25768
    Leathery Eggs (Ridley Scott, Zaonce): 24590
    Rusani Old Smokey (Fernandes Market, Rusani): 23240
    CD-75 Kitten Brand Coffee (Kirk Dock, CD-75 661): 18984
    Waters of Shintara (Jameson Memorial, Shinrarta Dezhra (permit)): 18550
    
### Optimize your routes:

It's easy to find the highest expected profits in the galaxy:

    > python .\edrg.py --optimize
    Optimal route: Geawen Dance Dust (Obruchev Legacy, Geawen): 26572
     and HIP Organophospates (Stasheff Colony, HIP 80364): 10010
     at a distance of 215.11 Ly with round-trip expected profit 813342

Of course, maybe you want to limit yourself to safer routes:

    > python .\edrg.py --optimize --filter "Goods.min_supply > 0" --filter "Station.dist < 1000"
    Optimal route: Altairian Skin (Solo Orbiter, Altair): 6846
     and Rajukru Multi-Stoves (Snyder Terminal, Rajukru): 10912
     at a distance of 169.03 Ly with round-trip expected profit 466372

Go nuts! Enjoy!

## API

There are three major classes you can operate on with this program: `System`, `Station`, and `Goods`. Fields are mostly self-explanatory, and appear below:

### System
* `System.name`
* `System.x`, `System.y`, `System.z`: coordinates in 3d space of the system
* `System.stations`: a list of stations in the system.

### Station
* `Station.name`
* `Station.system`: the system in which this station is located
* `Station.dist`: the distance of the station from the arrival point in-system
* `Station.goods`: the rare goods traded by this station

### Goods
* `Goods.name`
* `Goods.price`: price at the system of origin
* `Goods.max_cap`: Probably the goods stop spawning if you have more than this many. Unconfirmed.
* `Goods.min_supply`: the minimum amount which will spawn
* `Goods.max_supply`: the maximum amount which will ever spawn
* `Goods.expected_supply`: the average of `min_supply` and `max_supply`
* `Goods.min_value`: `price * min_supply`
* `Goods.max_value`
* `Goods.expected_value`

## Installation

1. Ensure you have Python 3 installed and available in your path.
2. Clone this repository onto your local machine
3. Navigate into the cloned directory in the shell of your choice
4. `pip install virtualenv` (use `sudo` as required)
5. `virtualenv .`
6. `./Scripts/activate` (or `activate.bat` for Windows command prompt, or `activate.ps1` for Windows Powershell)
7. `pip install -r requirements.txt`
8. You're good to go! 

## Usage

    usage: edrg.py [-h] [-w] [-c] [-d] [-o] [--optimize-outputs N]
                   [--max-dist MAX_DIST] [-l N] [-f FILTER] [-s SORT] [-a]
    
    Work with the Elite Dangerous Rare Goods
    
    optional arguments:
      -h, --help            show this help message and exit
      -w, --wipe            Wipe the database and recreate it from scratch from
                            the spreadsheet
      -c, --count           Return the number of goods meeting the specified
                            criteria
      -d, --display         Display the names of all goods meeting the specified
                            criteria
      -o, --optimize        Compute and display the optimal route given the
                            specified criteria
      --optimize-outputs N  Modifies --optimize: show the top N optimization
                            outputs. Default 1
      --max-dist MAX_DIST   Modifies --optimize: the maximal distance you'll
                            accept for a route
      -l N, --limit N       Limit to the first N SQL results. This happens before
                            optimization!
      -f FILTER, --filter FILTER
                            Raw SQLAlchemy filter strings. You have access to
                            Goods, Station, and System.
      -s SORT, --sort SORT  Raw SQLAlchemy order_by string. Sorts descending by
                            default. You have access to Goods, Station, and
                            System.
      -a, --ascending       Modifies --sort to produce an ascending sort instead.

## For the Future

I may come back to this to make it read from the [excellent source document](https://docs.google.com/spreadsheets/d/1haUVaFIxFq5IPqZugJ8cfCEqBrZvFFzcA-uXB4pTfW4/pubhtml) from which I pulled the raw data, instead of my modified local copy; that way it's more resilient to future updates. In the meantime, if you discover or find published a good which isn't in the database, just update the spreadysheet and run `edrg.py --wipe` to refresh it.