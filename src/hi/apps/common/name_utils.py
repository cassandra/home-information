import random


class RandomNameGenerator:

    ADJECTIVES = [
        'caring', 'hardworking', 'fun', 'sweet', 'loving', 'rational',
        'welcoming', 'wise', 'polite', 'quiet', 'quick', 'loyal',
        'truthful', 'understanding', 'amusing', 'sensible', 'awesome',
        'sturdy', 'adorable', 'adventurous', 'aggressive', 'alert',
        'attractive', 'average', 'beautiful', 'blue-eyed', 'blushing',
        'bright', 'clean', 'clear', 'cloudy', 'colorful', 'crowded',
        'cute', 'dark', 'distinct', 'elegant', 'excited', 'fancy',
        'glamorous', 'gleaming', 'gorgeous', 'graceful', 'groovy',
        'handsome', 'light', 'long', 'magnificent', 'misty', 'hip',
        'muddy', 'old-fashioned', 'plain', 'poised', 'precious', 'quaint',
        'shiny', 'smoggy', 'sparkling', 'spotless', 'stormy', 'strange',
        'unsightly', 'unusual', 'wide-eyed', 'alive', 'better', 'brainy',
        'breakable', 'busy', 'careful', 'cautious', 'clever', 'concerned',
        'crazy', 'curious', 'different', 'slick', 'difficult', 'doubtful',
        'easy', 'expensive', 'famous', 'fragile', 'gifted', 'helpful',
        'important', 'impossible', 'inexpensive', 'innocent',
        'inquisitive', 'modern', 'odd', 'open', 'outstanding', 'poor',
        'powerful', 'prickly', 'puzzled', 'real', 'rich', 'shy', 'sleepy',
        'super', 'talented', 'tame', 'tough', 'day', 'night',
        'vast', 'wandering', 'wild', 'agreeable', 'amused', 'radical',
        'brave', 'calm', 'charming', 'chaotic', 'cheerful', 'comfortable',
        'cooperative', 'courageous', 'delightful', 'determined', 'eager',
        'elated', 'enchanting', 'encouraging', 'energetic', 'enthusiastic',
        'exciting', 'exuberant', 'fair', 'faithful', 'fantastic', 'fine',
        'friendly', 'funky', 'funny', 'gentle', 'glorious', 'good',
        'happy', 'healthy', 'helpful', 'hilarious', 'incredible', 'jolly',
        'joyous', 'kind', 'lively', 'lovely', 'lucky', 'nice', 'obedient',
        'perfect', 'pleasant', 'proud', 'relieved', 'silly', 'smiling',
        'splendid', 'successful', 'thankful', 'thoughtful', 'victorious',
        'vivacious', 'witty', 'wonderful', 'zealous', 'zany', 'fabulous',
        'far-out', 'neat', 'nifty', 'groovy', 'grooviest', 'happiest', 'luckiest',
        'excellent', 'unorthodox', 'great', 'greatest', 'eccentric',
        'unconventional', 'bizarre', 'offbeat', 'original', 'unique',
        'authentic', 'trustworthy', 'credible', 'pure', 'legitimate',
        'reliable', 'decisive', 'stable', 'dependable', 'best', 'strong',
        'steady', 'durable', 'tenacious', 'vigorous', 'capable',
        'theoretical', 'spontaneous', 'affable', 'generous', 'charitable',
        'sincere', 'honest', 'wiley', 'tricky', 'psychedelic', 'candid',
        'earnest', 'genuine', 'heartfelt', 'cordial', 'hearty', 'profound',
        'warm', 'intelligent', 'philosophical', 'serious', 'subtle', 'logical',
        'serene', 'composed', 'stoic', 'unflappable', 'enlightened', 'scholarly',
        'sage', 'skilled', 'mysterious', 'discerning', 'brainy', 'cultivated',
        'cultured', 'savvy', 'studious', 'sophisticated', 'civilized', 'artful',
        'sharp', 'shrewd', 'keen', 'calculating', 'devoted', 'spirited',
        'vivacious', 'lighthearted', 'rocking', 'playful', 'upbeat', 'vibrant',
        'breezy', 'merry', 'animated', 'bold', 'passionate', 'peppy', 'gritty',
        'intrepid', 'heroic', 'valiant', 'gutsy', 'gallant', 'bodacious', 'noble',
        'whimsical', 'mirthful', 'snappy', 'erudite', 'enigmatic', 'obscure',
        'mystical', 'magical', 'incrutable', 'enchanted', 'uncanny', 'spellbinding',
        'marvelous', 'fascinating', 'extraordinary', 'mythical', 'charismatic',
        'transcendental', 'insightful', 'perceptive', 'knowledgeable', 'astute',
        'brilliant', 'judicious', 'prudent', 'skillful', 'sane', 'thorough',
        'diplomatic', 'discreet', 'informed', 'gracious', 'strategic', 'suave',
        'smooth', 'peaceful', 'polished', 'sleek', 'tranquil', 'amicable',
        'easygoing', ]

    ANIMAL_NOUNS = [
        'aardvark', 'albatross', 'alligator', 'alpaca', 'ant',
        'anteater', 'antelope', 'ape', 'armadillo', 'herd', 'baboon',
        'badger', 'barracuda', 'bat', 'bear', 'beaver', 'bee', 'bison',
        'boar', 'galago', 'butterfly', 'camel', 'caribou', 'cat',
        'caterpillar', 'cattle', 'chamois', 'cheetah', 'chicken',
        'chimpanzee', 'chinchilla', 'chough', 'clam', 'cobra', 'cockroach',
        'cod', 'cormorant', 'coyote', 'crab', 'herd', 'crocodile', 'crow',
        'curlew', 'deer', 'dinosaur', 'dog', 'dolphin', 'donkey',
        'dotterel', 'dove', 'dragonfly', 'duck', 'dugong', 'dunlin',
        'eagle', 'echidna', 'eel', 'elephant', 'elk', 'emu', 'falcon',
        'ferret', 'finch', 'fish', 'flamingo', 'fly', 'fox', 'frog',
        'gaur', 'gazelle', 'gerbil', 'giraffe', 'gnat', 'goat', 'goose',
        'goldfish', 'gorilla', 'goshawk', 'grasshopper', 'grouse',
        'guanaco', 'poultry', 'herd', 'gull', 'hamster', 'hare', 'hawk',
        'hedgehog', 'heron', 'herring', 'hippopotamus', 'hornet', 'horse',
        'human', 'hummingbird', 'hyena', 'jackal', 'jaguar', 'jay',
        'jellyfish', 'kangaroo', 'koala', 'kouprey', 'kudu', 'lapwing',
        'lark', 'lemur', 'leopard', 'lion', 'llama', 'lobster', 'locust',
        'loris', 'louse', 'lyrebird', 'magpie', 'mallard', 'manatee',
        'marten', 'meerkat', 'mink', 'monkey', 'moose', 'mouse',
        'mosquito', 'mule', 'narwhal', 'newt', 'nightingale', 'octopus',
        'okapi', 'opossum', 'oryx', 'ostrich', 'otter', 'owl', 'ox',
        'oyster', 'parrot', 'partridge', 'peafowl', 'pelican', 'penguin',
        'pheasant', 'pig', 'pigeon', 'pony', 'porcupine', 'porpoise',
        'quail', 'quelea', 'rabbit', 'raccoon', 'rat', 'raven', 'herd',
        'reindeer', 'rhinoceros', 'ruff', 'salamander', 'salmon',
        'sandpiper', 'sardine', 'scorpion', 'herd', 'seahorse', 'shark',
        'sheep', 'shrew', 'shrimp', 'skunk', 'snail', 'snake', 'spider',
        'squid', 'squirrel', 'starling', 'stingray', 'stinkbug', 'stork',
        'swallow', 'swan', 'tapir', 'tarsier', 'termite', 'tiger', 'toad',
        'trout', 'poultry', 'turtle', 'vulture', 'wallaby', 'walrus',
        'wasp', 'carabeef', 'weasel', 'whale', 'wolf', 'wolverine',
        'wombat', 'woodcock', 'woodpecker', 'worm', 'wren', 'yak', 'zebra',
    ]

    TRAVEL_NOUNS = [
        'adventurer', 'aeronaut', 'aircrew', 'alpinist', 'autoist', 'aviator',
        'backpacker', 'barnstormer', 'cabby', 'camper', 'captain',
        'charioteer', 'chauffeur', 'climber', 'coachman', 'commander',
        'copilot', 'cyclist', 'discoverer', 'driver',
        'excursionist', 'explorer', 'flyer', 'gadabout', 'gallivanter',
        'globetrotter', 'hackie', 'hiker', 'biker', 
        'jet-setter', 'journeyer', 'motorist', 'motorman', 'mountaineer',
        'navigator', 'nomad', 'passenger', 'pilgrim',
        'pilot', 'prospector', 'rambler', 'reconnoiterer', 'rider',
        'road-hog', 'roamer', 'rover', 'sailor', 'scout', 'seafarer',
        'sightseer', 'skipper', 'speeder', 'surveyor', 'tourer', 'tourist',
        'tramp', 'traveler', 'trekker', 'tripper', 'trouper', 'truant',
        'trucker', 'vacationer', 'vacationist', 'vagabond', 'vagrant',
        'viator', 'visitor', 'voyager', 'wanderer', 'wayfarer', 'wingman',
    ]

    COMPETITION_NOUNS = [
        'challenge', 'game', 'contest', 'event',
        'battle', 'skirmish', 'matchup', 'competition', 'match',
        'struggle', 'conflict', 'classic', 'open', 'round', 'heat', 'duel',
        'face-off', 'showdown', 'fray', 'endeavor', 'undertaking',
        'championship', 'meet', 'race','rivalry',
    ]
    
    @classmethod
    def next_first_name(cls):
        return random.choice( cls.ADJECTIVES ).capitalize()

    @classmethod
    def next_last_name(cls):
        return random.choice( cls.TRAVEL_NOUNS ).capitalize()
    
    @classmethod
    def next_full_name(cls):
        first_name = cls.next_first_name()
        last_name = cls.next_last_name()
        return f'{first_name} {last_name}'

    @classmethod
    def next_game_name(cls):
        adjective = random.choice( cls.ADJECTIVES ).capitalize()
        noun = random.choice( cls.COMPETITION_NOUNS ).capitalize()
        return f'{adjective} {noun}'
    
