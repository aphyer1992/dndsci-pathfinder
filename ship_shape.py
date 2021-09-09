import math
import random

def log_location(log_type):
    assert log_type in ['voyages_false', 'voyages_true', 'encounters_false', 'encounters_true', 'ships_available']
    if log_type == 'voyages_false':
        log_location = 'dndsci_pathfinder_player_voyage_log.csv'
    elif log_type == 'encounters_false':
        log_location = 'dndsci_pathfinder_player_encounter_log.csv'
    else:
        log_location = 'ship_log_{}.csv'.format(log_type)
    return(log_location)
                                               
def format_for_log(datapoint):
    if isinstance(datapoint, str):
        return(datapoint)

    if isinstance(datapoint, float):
        pct = 100*datapoint
        render_pct = math.ceil(pct - 0.00001) # to handle rounding etc.
        return('{}%'.format(render_pct))

    if isinstance(datapoint, int):
        return('{}'.format(datapoint))

    if isinstance(datapoint, tuple):
        return('{}{}'.format(datapoint[0], datapoint[1]))
    
    if isinstance(datapoint, Hex):
        datastring ='Hex {}'.format(datapoint.render_coords)
        if datastring == 'Hex Q6':
            datastring = 'Hex Q6 (Eastmarch)'
        elif datastring == 'Hex I3':
            datastring = 'Hex I3 (Norwatch)'
        elif datastring == 'Hex G13':
            datastring = 'Hex G13 (Westengard)'
        elif datastring == 'Hex P15':
            datastring = 'Hex P15 (South Point)'
        return(datastring)
    
    if datapoint is None:
        return('None')

    print('Object of unexpected type {}:'.format(type(datapoint)))
    print(datapoint)

    assert(False)
    
def log(log_type, contents, overwrite=False):
    location = log_location(log_type)
    contents = [ format_for_log(c) for c in contents ]
    message = ",".join(contents) + '\n'
    file = open(location, 'w' if overwrite else 'a')  # a = append mode
    file.write(message)

def setup_logs():
    log('voyages_false', [ 'Voyage ID', 'Origin Port', 'Date', 'Planned Route', 'Ship ID', 'Ship Name', 'Ship Type', 'Captain Name', 'Weeks Since Last Voyage', 'Voyage Destination', 'Voyage Purpose', 'Damage Taken' ], overwrite=True)
    log('voyages_true', [ 'Voyage ID', 'Origin Port', 'Date', 'Planned Route', 'Actual Route', 'Ship ID', 'Ship Name', 'Ship Type', 'Captain Name', 'Weeks Since Last Voyage', 'Voyage Destination', 'Voyage Purpose', 'Starting Health', 'Damage Taken' ], overwrite=True)
    log('encounters_true', ['Voyage ID', 'Ship ID', 'Ship Name', 'Encounter Hex', 'True Encounter Type', 'Logged Encounter Type', 'Damage Taken'], overwrite=True)        
    log('encounters_false', ['Voyage ID', 'Ship ID', 'Ship Name', 'Encounter Hex', 'Encounter Type', 'Damage Taken'], overwrite=True)
    log('ships_available', ['Ship ID', 'Ship Name', 'Ship Type' 'Captain Name', 'Weeks Since Last Voyage', 'Seamanship', 'Current Hull'], overwrite=True)

def revert_render_coords(coords):
    assert(len(coords) in [2,3])
    alphabet = [ 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z' ]
    new_coords = (alphabet.index(coords[0]), int(coords[1:]))
    return(new_coords)
            
def roll_die(x, num_dice=1):
    roll = 0
    dice_rolled = 0
    while dice_rolled < num_dice:
        rand = random.random()
        roll = roll + math.ceil(rand * x)
        dice_rolled = dice_rolled + 1
    return(roll)

def encounter_iceberg(ship):
    if roll_die(20) + ship.captain.seamanship < 5:
        return([roll_die(6), 'Iceberg'])
    else:
        return([0, None])

def encounter_sharks(ship):
    damage= min([roll_die(4) - 1, roll_die(4) - 1])
    return([damage, 'Sharks'])

def encounter_dragon(ship):
    dragon_roll = roll_die(6) + roll_die(6)
    damage = 0
    guns_damaged = 0
    while dragon_roll > 0 and damage < ship.current_hull:
        damage_to_dragon = max(0, ship.guns - guns_damaged)
        dragon_roll = max(0, dragon_roll - damage_to_dragon)
        damage = damage + dragon_roll
        if roll_die(3) == 1:
            guns_damaged = guns_damaged + 1
        
    return([damage, 'Dragon'])

def encounter_atlantean_merfolk(ship):
    sharkmaster = True if (roll_die(2) == 1 and 'Shark Trackers' not in ship.active_effects) else False
    if sharkmaster == True: # identical to the shark attack except with scouting
        damage= min([roll_die(4) - 1, roll_die(4) - 1])
        if 'Shark Trackers' not in ship.active_effects:
            ship.active_effects.append('Shark Trackers')
        return([damage, 'Sharks'])
    else: # Direct Attack
        total_damage = 0
        while True:
            damage = max(0,roll_die(8) - ship.guns) # waves of attacks until you fend one off.
            total_damage = total_damage + damage
            if damage == 0 or damage >= ship.current_hull: 
                break
        return([total_damage, 'Merfolk'])

def encounter_alexandrian_merfolk(ship):    
    if 'Storm Curse' not in ship.active_effects:
        ship.active_effects.append('Storm Curse')
    total_damage = 0
    while True:
        damage = max(0,roll_die(8) - ship.guns) # waves of attacks until you fend one off.
        total_damage = total_damage + damage
        if damage == 0: 
            break
    return([total_damage, 'Merfolk'])   
    
def encounter_reef(ship):
    stuck = True
    damage= 0
    false_lighthouse = True if len([n for n in ship.location.get_neighboring_hexes() if ('False Lighthouse' in n.notes)]) > 0 else False
    difficulty = 12 if false_lighthouse else 8
    while stuck:
        damage = damage + 1
        if roll_die(difficulty) <= ship.captain.seamanship:
            stuck = False
    return([damage, 'Reef'])

def encounter_pirates(ship, pirate_seamanship=1, pirate_guns=2, pirate_hull=10):
    pirate_damage_taken = 0
    ship_damage_taken = 0
    

    while(True):
        pirate_roll = roll_die(6)
        pirate_mod_roll = pirate_roll + pirate_seamanship
        captain_roll = roll_die(6)
        captain_mod_roll = captain_roll + ship.captain.seamanship
        if pirate_mod_roll >= captain_mod_roll:
            ship_damage_taken = ship_damage_taken + roll_die(3, num_dice=pirate_guns)
            if ship_damage_taken >= ship.current_hull:
                return([ship_damage_taken, 'Pirates'])

        if captain_mod_roll >= pirate_mod_roll:
            pirate_hull = pirate_hull - roll_die(3, num_dice=ship.guns)
            if pirate_hull <= 0:
                return([ship_damage_taken, 'Pirates'])

        #test for pirate retreat
        ship_pct_hp = (ship.current_hull - ship_damage_taken) / ship.max_hull
        pirate_pct_hp = (pirate_hull - pirate_damage_taken)/pirate_hull
        if(pirate_pct_hp < ship_pct_hp):
            return([ship_damage_taken, 'Pirates'])

def encounter_calamity(ship):
    ship.active_effects.append('Calamity Withdrawn')
    return(encounter_pirates(ship, pirate_seamanship=2, pirate_guns=2, pirate_hull=20))

def encounter_harpies(ship):
    harpy_roll = roll_die(6)
    damage = max(0,harpy_roll - ship.guns)
    if damage == 0:
        ship.active_effects.append('Harpies Afraid')
    return([damage, 'Harpies'])

def encounter_kraken(ship):
    kraken_roll = roll_die(6) + roll_die(6)
    damage = 0
    while kraken_roll > 0:
        kraken_roll = max(0, kraken_roll - ship.guns)
        damage = damage + kraken_roll
    return([damage, 'Kraken'])

def encounter_st_berts_fire(ship):
    damage = max(0,roll_die(4) - 2)
    return([damage, 'Wyrd Majick Fyre'])


def encounter_warlock(ship):
    die_size = random.choice([4,6,8,10,12,20])
    damage = roll_die(die_size)
    return([damage, 'Wyrd Majick Fyre'])

def encounter_storm(ship):
    storm_power = roll_die(8)
    
    damage = max(0,storm_power - ship.captain.seamanship)
    ship.active_effects.append('Caught In Storm')
    if roll_die(20) <= damage and ship.location.cached_distances['distance_from_land'] == 1: # we may get dashed upon rocks
        run_aground_damage = roll_die(6) + (0 if ship.is_small else roll_die(6))
        damage = damage + run_aground_damage
        # not doing this for annoying reasons
        # blown off course?
        # ship.stormblown_hex = blow_location
    return([damage, 'Storm'])

def encounter_maelstrom(ship):
    if roll_die(10) != 1:  #most ships just get hit by storms around the edges and never see the Maelstrom
        return(encounter_storm(ship))
    else: # a few are not so lucky
        return([999999, 'Maelstrom'])

class ShipType:
    def __init__(self, name, guns, hull, speed, small=False):
        self.name = name
        self.hull = hull
        self.guns = guns
        self.speed = speed
        self.is_small = small

class Captain:
    def assign_name(self):
        if self.noble:
            first = [ 'Adalbrecht', 'Alberich', 'Dietrich', 'Emerich', 'Ernst', 'Friedrich', 'Gerhart', 'Gottfried', 'Heinrich', 'Karl', 'Konrad', 'Manfred', 'Otto', 'Rudolf', 'Schaeffer', 'Siegfried', 'Ulbrecht', 'Wilhelm', 'Wolfgang' ]
            last = [ 'Alfeldt', 'Bismarck', 'Chlodwig', 'Grolman', 'Glucksberg', 'Kaulbach', 'Konig', 'Lundorf', 'Reinhardt', 'Schneider', 'Schonbern', 'Walderdorf', 'Zelig']
            titles = [ 'Lord', 'Baron', 'Sir', 'Count' ]
            self.first = random.choice(first)
            self.last = random.choice(last)
            self.title = random.choice(titles)
            self.name = self.title + ' ' + self.first + ' von ' + self.last
        else:
            first = [ 'Angus', 'Brandon', 'Bryan', 'Conall', 'Conor', 'Dyllon', 'Erin', 'Fergus', 'Jack', 'Kelly', 'Killian', 'Liam', 'Neil', 'Patrick', 'Rick', 'Ryan', 'Seamus', 'Sean' ]
            last = [ 'Aubrey', 'Blake', 'Bracken', 'Buchanan', 'Callahan', 'Cullen', 'Darry', 'Flyn', 'Hogan', 'Keating', 'MacArthur', 'MacDougal', 'Malone', "O'Brien", "O'Connell", "O'Malley", "O'Neal", 'Reagan', 'Sweeney', 'Teague' ]
            self.first = random.choice(first)
            self.last = random.choice(last)
            self.name = self.first + ' ' + self.last
        
    def __init__(self):
        self.noble = True if roll_die(3) == 1 else False
        pass_school = False
        while pass_school == False:
            self.seamanship = min([roll_die(3), roll_die(3)])
            if self.noble or self.seamanship == 3:
                pass_school = True
            elif self.seamanship == 2:
                pass_school = True if roll_die(2) == 2 else False
                
        self.assign_name()

class Voyage:
    def __init__(self, origin_port, destinations, voyage_category, cargo_type=None):
        self.origin_port = origin_port
        assert None not in destinations
        for d in destinations:
            assert d.terrain_type != 'Land'
        self.destinations = destinations
        self.log_destination = destinations[0] #will not be updated during voyage
        self.category = voyage_category
        self.cargo_type = cargo_type
        self.routes = []
        self.assign_routes()
        self.assigned = False
        self.ship = None
        self.log = []
        self.id = self.origin_port.world.get_voyage_id()
        self.origin_port.world.voyages.append(self)
        

    def update_destination(self):
        self.destinations.remove(self.destinations[0])
        self.routes.remove(self.routes[0])

    def assign_routes(self):
        ghost_hex = self.origin_port.location
        route_string = [ghost_hex.render_coords]
        total_steps = 0
        for dest in self.destinations:
            dest_route = []
            while ghost_hex != dest:
                valid_moves = ghost_hex.get_valid_moves_towards(dest)
                ghost_hex = random.choice(valid_moves)
                dest_route.append(ghost_hex)
                route_string.append(ghost_hex.render_coords)
                if ghost_hex.terrain_type != 'Port':
                    total_steps = total_steps + 1
            self.routes.append(dest_route)
            
        self.route_string = '-'.join(route_string)
        self.total_steps = total_steps

    def assign_ship(self, require_optimal=True):
        valid_ships = [ s for s in self.origin_port.get_ships() if s.voyage is None ]
        if require_optimal:
            # short voyages are assigned to small ships, long ones to large ships
            if self.total_steps <= 6:
                valid_ships = [ s for s in valid_ships if s.is_small == True ]
            elif self.total_steps >=9:
                valid_ships = [ s for s in valid_ships if s.is_small == False ]
            # and ships are given 5 weeks to rest, which guarantees at least 50% health
            valid_ships = [ s for s in valid_ships if s.time_since_voyage >= 5 ]
        
        if len(valid_ships):
            my_ship = random.choice(valid_ships)
            self.ship = my_ship
            my_ship.voyage = self
            self.assigned = True
        else:
            if require_optimal==False:
                assert(False)

class Port:
    def __init__(self, world, location, cargo_types, hullBonus=0, gunsBonus = 0, speedBonus=0):
        self.world = world
        self.location = location
        self.hullBonus = hullBonus
        self.gunsBonus = gunsBonus
        self.speedBonus = speedBonus
        self.cargo_types = cargo_types
        self.voyage_plot_overrides = None
        
    def get_bonuses(self):
        return({
            'hull' : self.hullBonus,
            'guns' : self.gunsBonus,
            'speed' : self.speedBonus,
            })

    def get_ships(self):
        return( [ s for s in self.world.ships if s.location == self.location ] )

    def build_ship(self, force_type=None):
        types = self.world.ship_types
        if force_type is not None:
            types = [t for t in types if t.name == force_type]
        else:
            # try to tend towards variety
            types_here = [s.shiptype for s in self.world.ships if s.location == self.location]
            random.shuffle(types_here)
            for avoid_type in types_here:
                if len(types) > 1:
                    types = [t for t in types if t != avoid_type]
            
        shiptype = random.choice(types)
        new_ship = Ship(shiptype, self)
        self.world.ships.append(new_ship)

    def create_cargo_voyage(self):
        cargo_type = random.choice(self.cargo_types)
        destination_port = None
        while destination_port is None or destination_port == self or cargo_type in destination_port.cargo_types:
            destination_port = random.choice(self.world.ports)
        return(Voyage(self, [destination_port.location], 'Cargo: {}'.format(cargo_type), cargo_type=cargo_type))

    def create_transfer_voyage(self, target_port):
        return(Voyage(self, [target_port.location], 'Transfer'))

    def create_scouting_voyage(self):
        scout_distance = random.choice([3,4,5])
        target_hex = self.location.get_random_hex_at_range(scout_distance, required_terrain_type='Water')
        assert target_hex.terrain_type == 'Water'
        assert self.location.terrain_type == 'Port'
        description = 'Scouting'
        if scout_distance == 3:
            description = 'Fishing'
        if roll_die(2) == 1:
            description = 'Fishing'
        return(Voyage(self, [target_hex, self.location], description))

    def create_voyage(self):
        if roll_die(2) == 1:
            return(self.create_cargo_voyage())
        else:
            return(self.create_scouting_voyage())

    def create_voyages(self):
        if self.voyage_plot_overrides is not None:
            self.voyages = self.voyage_plot_overrides
            self.voyage_plot_overrides = None
        else:
            voyages_to_assign = roll_die(4)
            voyages = []
            while len(voyages) < voyages_to_assign:
                voyages.append(self.create_voyage())

            for port in self.world.ports:
                if len(self.get_ships()) > 2 * len(port.get_ships()):
                    voyages.append(self.create_transfer_voyage(port))
                
            self.voyages = voyages
        

    def assign_voyages(self):
        for v in self.voyages:
            v.assign_ship()
        for v in self.voyages:
            if v.assigned == False and roll_die(2) == 1:
                v.assign_ship(require_optimal=False)

class Ship:
    def __init__(self, shiptype, port):
        self.shiptype = shiptype
        bonuses = port.get_bonuses()
        self.max_hull = self.shiptype.hull + bonuses['hull']
        self.guns = self.shiptype.guns + bonuses['guns']
        self.speed = self.shiptype.speed + bonuses['speed']
        self.current_hull = self.max_hull
        self.is_small = self.shiptype.is_small
        self.captain = Captain()
        self.assign_name(port)
        self.world = port.world
        self.id = self.world.get_ship_id()
        self.location = port.location
        self.voyage = None
        self.active_effects = [] # go away at the end of a voyage
        self.stormblown_hex = None
        self.time_since_voyage = 9999

    def assign_name(self, port):
        valid_name = False
        existing_names = port.world.all_ship_names()
        while valid_name == False:
            prefixes = [ 'White', 'Gray', 'Black', 'Red', 'Green', 'Golden', 'Silver', 'Rusty', 'Purple', 'Orange', 'Bloody', 'Mopey', 'Scurvy', 'Saucy']
            suffixes = [ 'Swan', 'Duck', 'Goose', 'Falcon', 'Hind', 'Bottom', 'Pearl', 'Heart', 'Diamond', 'Tortoise' ]
            prefix = random.choice(prefixes)
            suffix = random.choice(suffixes)
            name = prefix + ' ' + suffix
            if name not in existing_names:
                valid_name = True
        self.name = name
            

    def describe(self):
        print(
            'The {}.  {} under the command of Captain {} (Seamanship {}). Hull: {}/{} after {} weeks in Port.\n'.format(
                self.name, self.shiptype.name, self.captain.name, self.captain.seamanship, self.current_hull, self.max_hull, self.time_since_voyage
        ))

    def random_encounter(self):
        encounters = self.location.get_random_encounters(self)
        for enc in encounters:
            [ damage_taken, enc_description ] = enc['function'](self)
            pct_damage_taken = damage_taken / self.max_hull
            self.current_hull = max(0, self.current_hull - damage_taken)
            # real log for me
            log('encounters_true', [ self.voyage.id, self.id, self.name, self.location, enc['name'], enc_description, pct_damage_taken ])
            # delayed log for players
            if enc_description is not None:
                self.voyage.log.append([ self.voyage.id, self.id, self.name, self.location, enc_description, pct_damage_taken ])

    def destroy(self):
        self.location = None
        self.voyage = None
        self.world.ships.remove(self)

    def finish_and_log_voyage(self):
        log_damage = 'Destroyed' if self.current_hull == 0 else 1 -(self.current_hull / self.max_hull )
        log('voyages_true', [
            self.voyage.id, self.voyage.origin_port.location, self.world.display_date(), self.voyage.route_string, self.route_string, self.id, self.name,
            self.shiptype.name, self.captain.name, self.time_since_voyage if self.time_since_voyage < 9000 else 'Newly Built', self.voyage.log_destination, self.voyage.category, self.voyage_starting_health, log_damage
        ])
        log('voyages_false', [
            self.voyage.id, self.voyage.origin_port.location, self.world.display_date(), self.voyage.route_string, self.id, self.name,
            self.shiptype.name, self.captain.name, self.time_since_voyage if self.time_since_voyage < 9000 else 'Newly Built', self.voyage.log_destination, self.voyage.category, log_damage
        ])
        if self.current_hull == 0:
            self.destroy()
        else:
            for entry in self.voyage.log:
                log('encounters_false', entry)
            self.time_since_voyage = 0
            self.active_effects = []
        
    def execute_voyage(self):
        self.route_string = self.location.render_coords
        self.voyage_starting_health = self.current_hull / self.max_hull
        while len(self.voyage.destinations) and self.current_hull > 0:
            if self.stormblown_hex is not None:
                move_hex = self.stormblown_hex
                self.stormblown_hex = None
            else:
                if len(self.voyage.routes)==-0:
                    print('Weird has happened')
                    print('Current hex: {}'.format(self.location.coords))
                    print('Route taken: {}'.format(self.route_string))
                enroute_moves = [ m for m in self.location.get_neighboring_hexes() if m in self.voyage.routes[0] ]
                if len(enroute_moves): # stay on route, as close to destination as possible
                    enroute_moves.sort(key=lambda h: self.voyage.routes[0].index(h))
                    move_hex = enroute_moves[-1]
                else: # just try to close with destination
                    valid_moves = self.location.get_valid_moves_towards(self.voyage.destinations[0])
                    random.shuffle(valid_moves)
                    valid_moves.sort(key=lambda h: h.get_distance_to_hex(self.voyage.destinations[0]), reverse = True)
                    move_hex = valid_moves[-1]

                if self.captain.seamanship == 1 and roll_die(100) == 1: # mistake in navigation
                    mistake_hexes = [ m for m in self.location.get_neighboring_hexes() if m.get_distance_to_hex(move_hex) == 1 ] #adjacent to both current location and correct move
                    if len(mistake_hexes):
                        move_hex = random.choice(mistake_hexes)
                        if move_hex.terrain_type == 'Land':
                            self.active_effects.append('Run Aground')
                        
            self.location = move_hex
            self.route_string = '{}-{}'.format(self.route_string, self.location.render_coords)
            self.random_encounter()
            if 'Run Aground' in self.active_effects:
                self.active_effects.remove('Run Aground')
            if self.location == self.voyage.destinations[0]:
                self.voyage.update_destination()
    
        self.finish_and_log_voyage()

class Hex:
    def __init__(self, x, y, world):
        self.x = x
        self.y = y
        self.world = world
        self.terrain_type = 'Water'
        self.cached_distances = {}
        self.coords = (x,y)
        self.define_render_coords()
        self.notes = []

    def get_neighboring_hex_coords(self, omit_off_edge=True):
        output = [ (self.x, self.y+1), (self.x,self.y-1), (self.x+1, self.y), (self.x-1, self.y) ]
        if self.y%2 == 1:
            output.append((self.x+1, self.y+1))
            output.append((self.x+1, self.y-1))
        else:
            output.append((self.x-1, self.y+1))
            output.append((self.x-1, self.y-1))

        if omit_off_edge:
            output = [ h for h in output if h[0] >= 0 ]
            output = [ h for h in output if h[1] >= 0 ]
            output = [ h for h in output if h[0] < self.world.x_size ]
            output = [ h for h in output if h[1] < self.world.y_size ]

        return(output)

    def get_neighboring_hexes(self):
        coords = self.get_neighboring_hex_coords()
        output = []
        for coord in coords:
            output.append(self.world.get_hex_by_coords(coord))
        return(output)

    def get_distance_to_hex(self, target_hex):
        return(self.cached_distances[target_hex.coords])
               
    def get_valid_moves_towards(self, target_hex):
        neighbors = self.get_neighboring_hexes()
        valid_moves = [ n for n in neighbors if n.terrain_type in ['Water', 'Port'] ]
        min_dist = 99999
        min_dist_moves = []
        for move_hex in valid_moves:
            move_dist = move_hex.get_distance_to_hex(target_hex)
            if move_dist < min_dist:
                min_dist = move_dist
                min_dist_moves = []
            if move_dist == min_dist:
                min_dist_moves.append(move_hex)
        valid_moves = min_dist_moves
        if min_dist != self.get_distance_to_hex(target_hex) - 1:
            print('Something strange has happened.')
            print('We are in hex {}, trying to get to hex {} of type {}'.format(self.coords, target_hex.coords, target_hex.terrain_type))
            print('We are at distance {}, and think the best neighbor we can find is e.g. {}, at distance {}'.format(self.get_distance_to_hex(target_hex), valid_moves[0].coords, min_dist))
        assert min_dist == self.get_distance_to_hex(target_hex) - 1
        return(valid_moves)

    def get_random_hex_at_range(self, range_to_get, required_terrain_type=None):
        hexes = [ h for h in self.world.hexes if ( self.cached_distances[h.coords] == range_to_get ) ]
        if required_terrain_type is not None:
            hexes = [ h for h in hexes if h.terrain_type == required_terrain_type ]
        return(random.choice(hexes))

    def reef_probability(self):
        if self.cached_distances['distance_from_land'] > 1 or self.cached_distances['distance_from_port'] <= 1:
            return(0)
        elif len([n for n in self.get_neighboring_hexes() if ('False Lighthouse' in n.notes)]):
            return(0.4)
        else:
            return(0.2)

    def adjacent_to_warlock(self):
        necromancer_palace_location = 'Necromancer Summer Palace' if self.world.get_season() == 'Summer' else 'Necromancer Palace'
        necro_neighbors = [ n for n in self.get_neighboring_hexes() if necromancer_palace_location in n.notes ]
        return(True if len(necro_neighbors) else False)

    def distance_to_atlanteans(self):
        return( self.get_distance_to_hex(self.world.atlantean_location))
    
    def distance_to_alexandrians(self):
        return( self.get_distance_to_hex(self.world.alexandrian_location))
    
    def get_encounter_list(self, ship):
        calamity_enabled = True if ((self.cached_distances['distance_from_Calamity_Cove'] <= 2) and ('Calamity Withdrawn' not in ship.active_effects)) else False
        encounters = [
            {
                'name' : 'Pirates',
                'probability' : 0.0 if calamity_enabled else (0.12 / ship.speed),
                'function' : encounter_pirates,
            },
            {
                'name' : 'Dread Pirate Calamity',
                'probability' : (0.12 / ship.speed) if calamity_enabled else 0.0,
                'function' : encounter_calamity,
            },
            {
                'name' : 'Harpies',
                'probability' : ( 0.0 if 'Harpies Afraid' in ship.active_effects else ( 0.4 if ship.voyage.cargo_type == 'Magefruit' else 0.1 ) ) / ship.speed, # 
                'function' : encounter_harpies,
            },
            {
                'name' : 'Reef',
                'probability' : self.reef_probability() / (5 if ship.is_small else 1),
                'function' : encounter_reef,
            },
            {
                'name' : 'Kraken',
                'probability' : 0.3 if self.cached_distances['distance_from_land'] > 2 else 0.0,
                'function' : encounter_kraken,
            },
            {
                'name' : 'Iceberg',
                'probability' : 0.5 if self.get_temperature() == 'Cold' else 0.0,
                'function' : encounter_iceberg,
            },
            {
                'name' : 'Warlock',
                'probability' : 0.4 / ship.speed if self.adjacent_to_warlock() == True else 0.0,
                'function' : encounter_warlock,
            },
            {
                'name' : 'Atlantean Merfolk',
                'probability' : ((0.6 / ship.speed) * (3 if 'Shark Trackers' in ship.active_effects else 1)) if self.distance_to_atlanteans() <= 1 == True else 0.0,
                'function' : encounter_atlantean_merfolk,
            },
            {
                'name' : 'Alexandrian Merfolk',
                'probability' : (0.6 - (self.distance_to_alexandrians() * 0.2)) / ship.speed,
                'function' : encounter_alexandrian_merfolk,
            },
            {
                'name' : 'Sharks',
                'probability' : (0.2 if self.cached_distances['distance_from_land'] > 2 else 0.1) / ship.speed,
                'function' : encounter_sharks,
            },
            {
                'name' : 'Dragon',
                'probability' : 0.02 / ship.speed,
                'function' : encounter_dragon,
            },
            {
                'name' : 'Storm',
                'probability' : 0.07 * (3 if 'Storm Curse' in ship.active_effects else 1),
                'function' : encounter_storm,
            },
            {
                'name' : 'Maelstrom',
                'probability' : 0.1 if 'Maelstrom' in self.notes else 0.0,
                'function' : encounter_maelstrom,
            },
            {
                'name' : "St. Bert's Fire",
                'probability' : 0.01 if 'Caught In Storm' in ship.active_effects else 0,
                'function' : encounter_st_berts_fire
            },
        ]
        
        # once we get our small chance of fire we remove this
        if 'Caught In Storm' in ship.active_effects:
            ship.active_effects.remove('Caught In Storm')
        return([] if self.terrain_type == 'Port' else encounters)

    def get_random_encounters(self, ship):
        encounter_list = self.get_encounter_list(ship)
        encounters = []
        for encounter in encounter_list:
            if random.random() < encounter['probability']:
                encounters.append(encounter)
        return(encounters)
            
    def get_temperature(self):
        season = self.world.get_season()
        if season == 'Summer':
            effective_y = self.y + 4 # lower Y means further north means colder
        elif season == 'Winter':
            effective_y = self.y - 4
        else:
            effective_y = self.y
            
        if effective_y >= 14:
            return('Hot')
        elif effective_y <= 6:
            return('Cold')
        else:
            return('Warm')
    
    def define_render_coords(self):
        coords = self.coords
        alphabet = [ 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z' ]
        x_coord = alphabet[self.coords[0]]
        y_coord = self.coords[1]
        self.render_coords = '{}{}'.format(x_coord, y_coord)
        
class World:
    def __init__(self):
        print('Setting up map...')
        self.ships = []
        self.ports = []
        self.hexes = []
        self.voyages = []
        self.ship_id_increment = 0
        self.voyage_id_increment = 0
        self.expected_ships = 80
        self.week = 1
        self.month = 1
        self.year = 1407
        self.x_size = 19
        self.y_size = 17
        self.define_ship_types()
        self.init_hex_map()
        self.define_terrain()
        print('Precalculating distances...')
        self.calculate_travel_distances()
        self.build_ships(build_limit=self.expected_ships)

    def define_ship_types(self):                    
        dhow = ShipType('Dhow', 2, 20, 3, small=True)    
        barquentine = ShipType('Barquentine', 4, 20, 3)
        carrack = ShipType('Carrack', 2, 30, 3)
        galleon = ShipType('Galleon', 4 ,30, 1)

        self.ship_types = [ barquentine, carrack, dhow, galleon ]

    def init_hex_map(self):
        self.hex_map = []
        currentX = 0
        while currentX < self.x_size:
            column = []
            currentY = 0
            while currentY < self.y_size:
                new_hex = Hex(currentX, currentY, self)
                column.append(new_hex)
                self.hexes.append(new_hex)
                currentY = currentY + 1
            self.hex_map.append(column)
            currentX = currentX + 1

    def define_terrain(self):

        land_hex_coords = [
            (7,16), (8,16), (11,16), (7,15), (15,14), (3,14), (7,14), (14,13), (1,10), (2,10), (12,10), (1,9), (14,9), (9,8), (14,8), (17,8), (17,7),  (17,6), (2,5), (3,5),
            (6,3), (7,3),(11,3), (11,2), (12,2), (16,1), (8,0)
        ]
        self.land_hexes = [ self.get_hex_by_coords(c) for c in land_hex_coords ]    

        port_hex_coords = [(15,15), (6,13), (16,6), (8,3)]
        self.port_hexes = [ self.get_hex_by_coords(c) for c in port_hex_coords ]
        
        for port_hex in self.port_hexes:
            port_hex.terrain_type = 'Port'
            cargo_types = []
            if port_hex.coords == (15,15):
                cargo_types = [ 'Darkwood', 'Blackwine' ]
            elif port_hex.coords == (16,6):
                cargo_types = [ 'Magefruit', 'Scrolls' ]
            elif port_hex.coords == (6,13):
                cargo_types = ['Magefruit', 'Redstone' ]
            elif port_hex.coords == (8,3):
                cargo_types = [ 'Darkwood', 'Mythril' ]
            else:
                assert('False')
            self.ports.append(Port(self, port_hex, cargo_types))
        for land_hex in self.land_hexes:
            land_hex.terrain_type = 'Land'

        # ad hoc stuff
        self.get_hex_by_coords((17,8)).notes.append('False Lighthouse')
        self.get_hex_by_coords((9,8)).notes.append('Necromancer Palace')
        self.get_hex_by_coords((16,1)).notes.append('Necromancer Summer Palace')
        self.alexandrian_location = self.get_hex_by_coords((4,16))
        self.atlantean_path = [
            (5,5), (6,6), (6,7), (7,8), (7,9), (8,10), (8,11), (9,12), (9,13), # SE path
            (10,12), (10,11), (11,10), (11,9), (12,8), (12,7), (13,6), (13,5), # NE path
            (12,5), (11,5), (10,5), (9,5), (8,5), (7,5), (6,5), # W path
        ]
        self.atlantean_coords = (8,10)
        self.atlantean_location = self.get_hex_by_coords(self.atlantean_coords)
        maelstrom_hexes = [ (11,6), (11,7), (12,6) ]
        for maelstrom_hex in maelstrom_hexes:
            self.get_hex_by_coords(maelstrom_hex).notes.append('Maelstrom')
        self.calamity_coords = (12,10)
        self.calamity_location = self.get_hex_by_coords(self.calamity_coords)

    def print_terrain(self):
        for rowNumber in range(0,self.y_size):
            rowText = []
            for colNumber in range(0,self.x_size):
                rowText.append(self.get_hex_by_coords((colNumber, rowNumber)).terrain_type[0])
            rowText = '-'.join(rowText)
            if rowNumber%2==1:
                rowText = '-' + rowText
            else:
                rowText = rowText + '-'
            print(rowText)
            
    def get_ship_id(self):
        self.ship_id_increment = self.ship_id_increment + 1
        return(self.ship_id_increment)

    def get_voyage_id(self):
        self.voyage_id_increment = self.voyage_id_increment + 1
        return(self.voyage_id_increment)

    def month_as_string(self):
        months = [ 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ]
        return(months[(self.month%12)-1])
    
    def display_date(self):
        return('{} {} Week {}'.format(self.month_as_string(), self.year, self.week))
    
    # Given an array of one or more hexes, precalculate distance to that hex/hexes for all hexes in the map, store in the cached_distances dictionary of each hex
    def calculate_distance_to(self, hexes, storage_key, allow_land=False):
        # initialize to 0 for the hex(es) themselves, 999999 for everything else
        for iterate_hex in self.hexes:
            iterate_hex.cached_distances[storage_key] = 999999
        for base_hex in hexes:
            base_hex.cached_distances[storage_key] = 0

        iterationNeeded = True
        while iterationNeeded:
            iterationNeeded = False
            for iterate_hex in self.hexes:
                current_dist = iterate_hex.cached_distances[storage_key]
                neighbors = iterate_hex.get_neighboring_hexes()
                if allow_land == False:
                    neighbors = [ n for n in neighbors if n.terrain_type != 'Land' ]
                for n in neighbors:
                    implied_dist = n.cached_distances[storage_key] + 1
                    if implied_dist < current_dist:
                        iterationNeeded = True
                        iterate_hex.cached_distances[storage_key] = implied_dist
            
    def calculate_travel_distances(self):
        self.calculate_distance_to(self.land_hexes+self.port_hexes, 'distance_from_land', allow_land=True)
        self.calculate_distance_to([self.calamity_location], 'distance_from_Calamity_Cove', allow_land=True)
        self.calculate_distance_to(self.port_hexes, 'distance_from_port')
        for distance_hex in self.hexes:
            self.calculate_distance_to([distance_hex], distance_hex.coords)
        
    def get_hex_by_coords(self, coords):
        if type(coords) == 'string':
            coords = revert_render_coords(coords)
        return(self.hex_map[coords[0]][coords[1]])

    def get_season(self):
        if self.month in [12, 1, 2]:
            return('Winter')
        elif self.month in [3, 4, 5]:
            return('Spring')
        elif self.month in [6, 7, 8]:
            return('Summer')
        else:
            return('Fall')

    def all_ship_names(self):
        names = []
        for ship in self.ships:
            names.append(ship.name)
        return(names)

    def build_ship(self):
        building_port = random.choice(self.ports)
        building_port.build_ship()

    def build_ships(self, build_limit=-1):
        if build_limit == -1:
            build_limit = len(self.ports)
        missing_ships = self.expected_ships - len(self.ships)
        ships_to_build = min(missing_ships, build_limit)
        ships_built = 0  
        while ships_built < ships_to_build:
            self.build_ship()
            ships_built = ships_built + 1
        
    def prepare_voyages(self):
        for port in self.ports:
            port.create_voyages()
            port.assign_voyages()      

    def execute_voyages(self):
        for voyage in self.voyages:
            if voyage.ship is not None:
                voyage.ship.execute_voyage()

    def clear_voyages(self):
        self.voyages = []
        for port in self.ports:
            port.voyages = []
        for ship in self.ships:
            ship.voyage = None

    def repair_ships(self):
        for ship in self.ships:
            ship.current_hull = min(ship.max_hull, ship.current_hull + (ship.max_hull / 10))
            ship.time_since_voyage = ship.time_since_voyage + 1

    def move_atlanteans(self):
        atlantean_index = self.atlantean_path.index(self.atlantean_location.coords)
        new_index = (atlantean_index + 1)%(len(self.atlantean_path))
        self.atlantean_location = self.get_hex_by_coords(self.atlantean_path[new_index])

    def advance_time(self):
        self.week = self.week + 1
        if self.week == 5:
            self.week = 1
            self.month = self.month + 1
            if self.month == 13:
                self.month = 1
                print('Finished {}\n'.format(self.year))
                self.year = self.year + 1

    def print_ship_counts(self):
        print('Port ship counts: ' + ', '.join([str(len(p.get_ships())) for p in self.ports]))
    
    def main_loop(self):
        self.build_ships()
        self.prepare_voyages()
        self.execute_voyages()
        self.clear_voyages()
        self.repair_ships()
        self.move_atlanteans()
        self.advance_time()

def read_log_file(log_type):
    loc = log_location(log_type)
    file = open(loc, 'r')
    data = file.readlines()
    rows = []
    keys = None
    for entry in data:
        split_entry = entry.split(',')
        split_entry = [ s.rstrip('\n') for s in split_entry ]
        if keys is None:
             keys = split_entry
        else:
            row_dict = {}
            for i in range(0, len(split_entry)):
                row_dict[keys[i]] = split_entry[i]
            rows.append(row_dict)
    return(rows)
                         
def summarize_logs():
    voyage_logs = read_log_file('voyages_true')
    count = len(voyage_logs)
    dest_voyages = [v for v in voyage_logs if v['Damage Taken'] == 'Destroyed']
    dest = len(dest_voyages)
    print('{} voyages made.'.format(count))
    print('{}/{} ships destroyed ({:.1f}%).'.format(dest, count, 100*dest / count))

    for ship_type in ['Dhow', 'Barquentine', 'Carrack', 'Galleon']:
        ship_logs = [v for v in voyage_logs if v['Ship Type'] == ship_type ]
        ship_count = len(ship_logs)
        ship_dest_voyages = [v for v in ship_logs if v['Damage Taken'] == 'Destroyed']
        ship_dest = len(ship_dest_voyages)
        print('{}s only: {} voyages made, {}/{} times destroyed ({:.1f}%).'.format(ship_type, ship_count, ship_dest, ship_count, 100*ship_dest / ship_count))

    dest_ids = [v['Voyage ID'] for v in dest_voyages]
    encounter_logs = read_log_file('encounters_true')
    dest_encounter_logs = [e for e in encounter_logs if e['Voyage ID'] in dest_ids]
    dest_by = {}
    for e in dest_encounter_logs:
        enc_type = e['True Encounter Type']
        v_id = e['Voyage ID']
        dest_by[v_id] = enc_type
    dest_by_count = {}
    for d in dest_by.keys():
        e = dest_by[d]
        if e in dest_by_count.keys():
            dest_by_count[e] = dest_by_count[e] + 1
        else:
            dest_by_count[e] = 1
    for e in dest_by_count.keys():
        print('{} destroyed by {}'.format(dest_by_count[e], e))
    
    damage_count = {}
    enc_count = {}
    total_damage = 0
    for e in encounter_logs:
        d_taken = int(e['Damage Taken'].rstrip('%'))
        d_taken = min(d_taken, 100)
        total_damage = total_damage + d_taken
        e_type = e['True Encounter Type']
        if e_type in damage_count.keys():
            damage_count[e_type] = damage_count[e_type] + d_taken
            enc_count[e_type] = enc_count[e_type] + 1
        else:
            damage_count[e_type] = d_taken
            enc_count[e_type] = 1
            
    for e in damage_count.keys():
        print('{:.1f}% of total damage done by {}.  Average damage {:.1f}% per fight.'.format(damage_count[e]*100/total_damage, e, damage_count[e] / enc_count[e]))

    ports = ['Hex P15 (South Point)', 'Hex G13 (Westengard)', 'Hex I3 (Norwatch)', 'Hex Q6 (Eastmarch)']
    port_pairs = []
    for i in range(0, len(ports)):
        for j in range(0, len(ports)):
            if j > i:
                port_pairs.append((ports[i],ports[j]))

    for port_pair in port_pairs:
        print('Voyages between {} and {}'.format(port_pair[0], port_pair[1]))
        pair_voyages = [v for v in voyage_logs if v['Origin Port'] in port_pair and v['Voyage Destination'] in port_pair]
        pair_lost = [v for v in pair_voyages if v['Damage Taken'] == 'Destroyed']
        print('{}/{} successful ({:.1f}% destroyed)'.format(len(pair_voyages) - len(pair_lost), len(pair_voyages), len(pair_lost) * 100 / len(pair_voyages)))
        
def test_voyage(start_port, route_to_coords, ship_type, force_current_hull=None, force_seamanship=None, fixed_route=None, verbose=False, num_to_run=10000):
    run = 0
    passed = 0
    partial_passed = 0
    failed = 0
    assert(start_port.location.coords == (16,6))
    progress_pct = num_to_run / 10
    while run < num_to_run:
        if run % progress_pct == 0:
            print('{}% done'.format(run * 10/progress_pct))
        start_port.build_ship(force_type=ship_type)
        voyaging_ship = myWorld.ships[-1]
        if force_seamanship is not None:
            voyaging_ship.captain.seamanship = force_seamanship
        if force_current_hull is not None:
            voyaging_ship.current_hull = force_current_hull
        
        voyage = Voyage(start_port, [myWorld.get_hex_by_coords(route_to_coords), start_port.location], 'Mission')
        
        if fixed_route is not None:
            reverse_route = list(fixed_route)
            reverse_route.reverse()
            voyage.routes = [
                [ voyaging_ship.world.get_hex_by_coords(c) for c in fixed_route[1:]],
                [ voyaging_ship.world.get_hex_by_coords(c) for c in reverse_route[1:]]
            ]

        voyage.ship = voyaging_ship
        voyaging_ship.voyage = voyage
        voyage.assigned = True
        voyaging_ship.execute_voyage()
        if voyaging_ship.current_hull > 0:
            passed = passed + 1
            assert(len(voyage.destinations) == 0)
            voyaging_ship.destroy()
        else:
            assert(len(voyage.destinations) >= 1)
            if len(voyage.destinations) == 2:
                failed = failed + 1
            else:
                partial_passed = partial_passed + 1
        run = run + 1
        del(voyaging_ship)
    assert(run == passed + partial_passed + failed)
    print('{}/{} voyages made it to the objective ({:.1f}%)'.format(passed + partial_passed, run, 100*(passed + partial_passed) / run))
    print('{}/{} voyages made it back as well ({:.1f}%)'.format(passed, run, 100*(passed) / run))    

def simulate_test(route, ship_name=None, seamanship=None, shiptype=None, current_hull=None, verbose=False):
    start_port = myWorld.ports[2]
    assert(start_port.location.coords == (16,6))

    if ship_name is not None:
        ships = [s for s in myWorld.ships if s.location == start_port.location and s.name == ship_name]
        assert(len(ships)==1)
        ship = ships[0]
        seamanship = ship.captain.seamanship
        shiptype = ship.shiptype.name
        current_hull = ship.current_hull

    split_route = route.split('-')
    destination = revert_render_coords(split_route[-1])

    if current_hull == None:
        current_hull = 30 if shiptype in ['Carrack', 'Galleon'] else 20

    print('Testing the {} (a {} with HP {} and a Seamanship {} captain) on route {}'.format(ship_name if ship_name is not None else 'Test Ship', shiptype, current_hull, seamanship, route))

    if split_route[0] == 'Admiralty':     
        test_voyage(start_port, destination, shiptype, force_current_hull = current_hull, force_seamanship=seamanship, fixed_route=None, verbose=verbose)
    else:
        split_route = [ revert_render_coords(c) for c in split_route ]
        test_voyage(start_port, destination, shiptype, force_current_hull=current_hull, force_seamanship=seamanship, fixed_route=split_route, verbose=verbose) 
    

random.seed('dndsci_pathfinder')
setup_logs()
print('Performing world setup:')
myWorld = World()
while myWorld.year < 1420 or myWorld.month < 6:
    myWorld.main_loop()

# force voyages for one port
capitalPort = [ p for p in myWorld.ports if p.location.coords == (16,6) ][ 0 ]
v1 = Voyage(capitalPort, [myWorld.get_hex_by_coords((14,7)), capitalPort.location], 'Scouting')
v2 = Voyage(capitalPort, [myWorld.get_hex_by_coords((12,4)), capitalPort.location], 'Scouting')
# 'Pretend magefruit' for the logs
v3 = Voyage(capitalPort, [myWorld.get_hex_by_coords((6,13))], 'Cargo: Magefruit', cargo_type='Pretend Magefruit')
v4 = Voyage(capitalPort, [myWorld.get_hex_by_coords((7,4)), myWorld.get_hex_by_coords((8,3))], 'Cargo: Magefruit', cargo_type='Pretend Magefruit')
v4.log_destination = myWorld.get_hex_by_coords((8,3))
v4.route_string = 'Q6-P6-O6-N5-M5-L5-K5-K4-J4-I3'
# manually add reef encounter on unloading
capitalPort.voyage_plot_overrides = [v1,v2,v3,v4]
myWorld.main_loop()
#require that the last round of plot voyages worked.  If this doesn't happen, try a new seed.
assert(v1.destinations == [] )
assert(v2.destinations == [] )
assert(v3.destinations == [] )
assert(v4.destinations == [] )
# for hint purposes, add a reef encounter in H4 for v4 if one doesn't exist.


#summarize_logs()
                
print('SHIPS AVAILABLE IN CAPITAL:\n')
available_ships = [ s for s in myWorld.ships if s.location == capitalPort.location ]
for ship in available_ships:
    log('ships_available', [ship.id, ship.name, ship.shiptype.name, ship.captain.name, ship.time_since_voyage, ship.captain.seamanship, ship.current_hull])
    ship.describe()

#simulate_test('Q6-P6-O6-N6-M7-M8-L8-K9-K10-K11-L12-L13', 'Saucy Heart')

