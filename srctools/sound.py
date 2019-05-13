"""Reads and writes Soundscripts and Soundscapes."""
from enum import Enum

from srctools import Property, conv_float

from typing import (
    Optional, Union, TypeVar,
    List, Tuple, Dict,
    Iterable, Type, Callable,
    TextIO,
)


class Pitch(float, Enum):
    PITCH_NORM = 100.0
    PITCH_LOW = 95.0
    PITCH_HIGH = 120.0
    
    def __str__(self):
        return self.name


class VOLUME(Enum):
    """Special value, substitutes default volume (usually 1)."""
    VOL_NORM = 'VOL_NORM'

VOL_NORM = VOLUME.VOL_NORM


class Channel(Enum):
    """Different categories of sounds."""
    DEFAULT = "CHAN_AUTO"
    GUNFIRE = "CHAN_WEAPON"
    VOICE = "CHAN_VOICE"
    TF2_ANNOUNCER = "CHAN_VOICE2"
    ITEMS = "CHAN_ITEM"
    BODY = "CHAN_BODY"
    STREAMING = "CHAN_STREAM"
    CON_CMD = "CHAN_REPLACE"
    BACKGROUND = "CHAN_STATIC"
    PLAYER_VOICE = "CHAN_VOICE_BASE"

    #CHAN_USER_BASE+<number>
    #Custom channels can be defined here.


class Level(Enum):
    """Soundlevel constants - attenuation."""
    SNDLVL_NONE = 'SNDLVL_NONE'
    SNDLVL_20dB = 'SNDLVL_20dB'
    SNDLVL_25dB = 'SNDLVL_25dB'
    SNDLVL_30dB = 'SNDLVL_30dB'
    SNDLVL_35dB = 'SNDLVL_35dB'
    SNDLVL_40dB = 'SNDLVL_40dB'
    SNDLVL_45dB = 'SNDLVL_45dB'
    SNDLVL_50dB = 'SNDLVL_50dB'
    SNDLVL_55dB = 'SNDLVL_55dB'
    SNDLVL_IDLE = 'SNDLVL_IDLE'
    SNDLVL_65dB = 'SNDLVL_65dB'
    SNDLVL_STATIC = 'SNDLVL_STATIC'
    SNDLVL_70dB = 'SNDLVL_70dB'
    SNDLVL_NORM = 'SNDLVL_NORM'
    SNDLVL_80dB = 'SNDLVL_80dB'
    SNDLVL_TALKING = 'SNDLVL_TALKING'
    SNDLVL_85dB = 'SNDLVL_85dB'
    SNDLVL_90dB = 'SNDLVL_90dB'
    SNDLVL_95dB = 'SNDLVL_95dB'
    SNDLVL_100dB = 'SNDLVL_100dB'
    SNDLVL_105dB = 'SNDLVL_105dB'
    SNDLVL_110dB = 'SNDLVL_110dB'
    SNDLVL_120dB = 'SNDLVL_120dB'
    SNDLVL_125dB = 'SNDLVL_125dB'
    SNDLVL_130dB = 'SNDLVL_130dB'
    SNDLVL_GUNFIRE = 'SNDLVL_GUNFIRE'
    SNDLVL_140dB = 'SNDLVL_140dB'
    SNDLVL_145dB = 'SNDLVL_145dB'
    SNDLVL_150dB = 'SNDLVL_150dB'
    SNDLVL_180dB = 'SNDLVL_180dB'
    
    def __str__(self):
        return self.name
        
class Position(Enum):
    """Represents special positions for soundscapes."""
    RAND = 'random'
    
    # Specified on the entity.
    POS_0 = 0
    POS_1 = 1
    POS_2 = 2
    POS_3 = 3
    POS_4 = 4
    POS_5 = 5
    POS_6 = 6
    POS_7 = 7
    

EnumType = TypeVar('EnumType', bound=Enum)


def split_float(
    val: str, 
    enum: EnumType, 
    default,
) -> Tuple[Union[float, EnumType], Union[float, EnumType]]:
    """Handle values which can be either single or a low, high pair of numbers.
    
    If single, low and high are the same.
    enum is a Enum with values to match text constants.
    """
    if ',' in val:
        s_low, s_high = val.split(',')
        try: 
            low = enum(s_low.upper())
        except ValueError:
            low = conv_float(s_low, default)
        try: 
            high = enum(s_high.upper())
        except ValueError:
            high = conv_float(s_high, default)
        return low, high
    else:
        try: 
            out = enum(val.upper())
        except ValueError:
            out = conv_float(val, default)
        return out, out


def join_float(val: Tuple[Union[Enum, float], Union[Enum, float]]) -> str:
    """Reverse split_float()."""
    low, high = val
    if low == high:
        return str(low)
    else:
        return '{!s},{!s}'.format(low, high)


class Sound:
    """Represents a single sound in the list."""
    def __init__(
        self,
        name: str,
        sounds: List[str],
        volume: Tuple[Union[float, VOLUME], Union[float, VOLUME]],
        channel: Channel,
        level: Tuple[Union[float, Level], Union[float, Level]],
        pitch: Tuple[Union[float, Pitch], Union[float, Pitch]],
        
        # Operator stacks
        stack_start: Optional[Property],
        stack_update: Optional[Property],
        stack_stop: Optional[Property],
    ):
        """Create a soundscript."""
        self.name = name
        self.volume = volume
        self.sounds = sounds
        self.channel = channel
        self.level = level
        self.pitch = pitch
        
        self.stack_start = stack_start
        self.stack_update = stack_update
        self.stack_stop = stack_stop
       
    @classmethod 
    def parse(cls, file: Property) -> Dict[str, 'Sound']:
        """Parses a soundscript file.
        
        This returns a dict mapping casefolded names to Sounds.
        """
        sounds = {}
        for snd_prop in file:
            volume = split_float(
                snd_prop['volume', '1'],
                VOLUME,
                1.0,
            )
            pitch = split_float(
                snd_prop['pitch', '100'],
                Pitch,
                100.0,
            )
            
            level = split_float(
                snd_prop['soundlevel', 'SNDLVL_NORM'],
                Level,
                Level.SNDLVL_NORM,
            )
            
            # Either 1 "wave", or multiple in "rndwave".
            wavs = []
            for prop in snd_prop:
                if prop.name == 'wave':
                    wavs.append(prop.value)
                elif prop.name == 'rndwave':
                    for subprop in prop:
                        wavs.append(subprop.value)

            channel = Channel(snd_prop['channel', 'CHAN_AUTO'])
            
            sound_version = snd_prop.int('soundentry_version', 1)
            
            if 'operator_stacks' in snd_prop:
                if sound_version == 1:
                    raise ValueError(
                        'Operator stacks used with version '
                        'less than 2 in "{}"!'.format(snd_prop.real_name))
                
                start_stack, update_stack, stop_stack = [
                    Property(stack_name, [
                        prop.copy()
                        for prop in 
                        snd_prop.find_children('operator_stacks', stack_name)
                    ])
                    for stack_name in 
                    ['start_stack', 'update_stack', 'stop_stack']
                ]
            else:
                start_stack, update_stack, stop_stack = [
                    Property(stack_name, [])
                    for stack_name in 
                    ['start_stack', 'update_stack', 'stop_stack']
                ]
            
            sounds[snd_prop.name] = Sound(
                snd_prop.real_name,
                wavs,
                volume,
                channel,
                level,
                pitch,
                start_stack,
                update_stack,
                stop_stack,
            )
        return sounds

    def export(self, sounds: Iterable['Sound'], file: TextIO):
        """Write SoundScripts to a file.
        
        Pass a file-like object open for text writing, and an iterable
        of Sounds to write to the file.
        """
        for snd in sounds:
            file.write('"{}"\n\t{{\n'.format(snd.name))
            
            file.write('\t' 'channel {}\n'.format(snd.channel.value))
            
            file.write('\t' 'soundlevel {}\n'.format(join_float(snd.level)))
            
            if snd.volume != (1, 1):
                file.write('\tvolume {}\n'.format(join_float(snd.volume)))
            if snd.pitch != (100, 100):
                file.write('\tpitch {}\n'.format(join_float(snd.pitch)))
            
            if len(snd.sounds) > 1:
                file.write('\trandwav\n\t\t{\n')
                for wav in snd.sounds:
                    file.write('\t\twave "{}"\n'.format(wav))
                file.write('\t\t}\n')
            else:
                file.write('\twave "{}"\n'.format(snd.sounds[0]))
            
            if snd.stack_start or snd.stack_stop or snd.stack_update:
                file.write(
                    '\t' 'soundentry_version 2\n'
                    '\t' 'operator_stacks\n'
                    '\t\t' '{\n'
                )
                if snd.stack_start:
                    file.write(
                        '\t\t' 'start_stack\n'
                        '\t\t\t' '{\n'
                    )
                    for prop in snd.stack_start:
                        for line in prop.export():
                            file.write('\t\t\t' + line)
                    file.write('\t\t\t}\n')
                if snd.stack_update:
                    file.write(
                        '\t\t' 'update_stack\n'
                        '\t\t\t' '{\n'
                    )
                    for prop in snd.stack_update:
                        for line in prop.export():
                            file.write('\t\t\t' + line)
                    file.write('\t\t\t}\n')
                if snd.stack_stop:
                    file.write(
                        '\t\t' 'stop_stack\n'
                        '\t\t\t' '{\n'
                    )
                    for prop in snd.stack_stop:
                        for line in prop.export():
                            file.write('\t\t\t' + line)
                    file.write('\t\t\t}\n')
                file.write('\t\t}\n')
            file.write('\t}\n')
            
class SubScape:
    """A reference to a child soundscape that will also play."""
    def __init__(
        self,
        name: str,
        volume: float,
        pos_offset: Optional[Position],
        pos_over: Optional[Position],
        pos_ambient: Optional[Position],
    ) -> None:
        self.name = name
        self.pos_offset = pos_offset
        self.pos = pos_over
        self.pos_ambient = pos_ambient
        
    @staticmethod
    def _parse_pos(prop: Property, kv: str) -> Optional[Position]:
        value = prop[kv, '']
        if value:
            try:
                return Position(int(value))
            except (ValueError, TypeError):
                raise ValueError('Invalid "{}" value!'.format(kv))
        else:
            return None

    @classmethod
    def parse(cls, prop: Property) -> 'SubScape':
        return cls(
            prop['name'],
            prop.float('volume'),
            cls._parse_pos(prop, 'position'),
            cls._parse_pos(prop, 'positionoverride'),
            cls._parse_pos(prop, 'ambientpositionoverride'),
        )
        
class LoopScape:
    """A looping sound that plays whilst a soundscape is active."""
        
class RandScape:
    """A set of non-looping sounds that randomly play at intervals."""

class Scape:
    """Represents a soundscape."""
    def __init__(
        self,
        name: str,
        fadetime: float=0.0,
        soundmixer: str='',
        dsp_preset: Optional[str]=None,
        dsp_volume: float=1.0,
        dsp_spatial: int=0,
        
        children: Iterable[SubScape]=(),
        snd_random: Iterable[RandScape]=(),
        snd_looping: Iterable[LoopScape]=(),
    ) -> None:
        self.name = name
        self.fadetime = fadetime
        self.soundmixer = soundmixer
        self.dsp_preset = dsp_preset
        self.dsp_volume = dsp_volume
        self.dsp_spatial = dsp_spatial
        
        self.children = list(children)
        self.snd_random = list(snd_random)
        self.snd_looping = list(snd_looping)
    
    @staticmethod
    def parse(
        props: Property,
    ) -> Dict[str, 'Scape']:
        """Parse soundscripts from a property tree."""
        scapes = {}  # type: Dict[str, Scape]
        
        for prop in props:
            
            if 'dsp' in prop:
                dsp_preset = prop.int('dsp', 0)
                dsp_volume = prop.float('dsp_volume', 1.0)
                dsp_spatial = prop.int('dsp_spatial', 0)  # Check default
            else:
                dsp_preset = None
                dsp_volume = 1.0
                dsp_spatial = 0
            
            
            scapes[prop.name] = Scape(
                prop.real_name,
                prop.float('fadetime', 0.0),
                prop['soundmixer', ''],
                dsp_preset,
                dsp_spatial,
                dsp_volume
            )
