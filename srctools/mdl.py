"""Parses Source models, to extract metadata."""
from typing import (
    Union, Iterator, Iterable,
    List, Dict, Tuple, NamedTuple,
    BinaryIO,
)
from enum import IntFlag, Enum
from pathlib import PurePosixPath

from srctools import Property
from srctools.binformat import (
    struct_read, read_nullstr, read_offset_array,
    str_readvec,
)
from srctools.filesys import FileSystem, File
from srctools.vec import Vec
from struct import Struct


IncludedMDL = NamedTuple('IncludedMDL', [
    ('label', str),
    ('filename', str),
])

SeqEvent = NamedTuple('SeqEvent', [
    # AnimEvents for known common ones, str for dynamic NPC-specific events.
    ('type', Union['AnimEvents', str]),
    ('cycle', float),
    ('options', str),
])

MDLSequence = NamedTuple('Sequence', [
    ('label', str),
    ('act_name', str),
    ('flags', int),
    ('act_weight', int),
    ('events', List[SeqEvent]),
    ('bbox_min', Vec),
    ('bbox_max', Vec),
    # More after here.
    ('keyvalues', str),
])


class Flags(IntFlag):
    """Flags for studio models."""
    autogenerated_hitbox = 1 << 0
    uses_env_cubemap = 1 << 1
    force_opaque = 1 << 2
    translucent_twopass = 1 << 3
    static_prop = 1 << 4
    uses_fb_texture = 1 << 5
    hasshadowlod = 1 << 6
    uses_bumpmapping = 1 << 7
    use_shadowlod_materials = 1 << 8
    obsolete = 1 << 9
    unused = 1 << 10
    no_forced_fade = 1 << 11
    force_phoneme_crossfade = 1 << 12
    constant_directional_light_dot = 1 << 13
    flexes_converted = 1 << 14
    built_in_preview_mode = 1 << 15
    ambient_boost = 1 << 16
    do_not_cast_shadows = 1 << 17
    cast_texture_shadows = 1 << 18


class AnimEventTypes(IntFlag):
    """Categories of animation events."""
    NONE = 0
    SERVER    = 1 << 0
    SCRIPTED  = 1 << 1
    SHARED    = 1 << 2
    WEAPON    = 1 << 3
    CLIENT    = 1 << 4
    FACEPOSER = 1 << 5

CL = AnimEventTypes.CLIENT
SV = AnimEventTypes.SERVER


class AnimEvents(Enum):
    """The types of events in models.

    0    -  999 is "specific" / new string-based type.
    1000 - 1999 is for scripted events.
    2000 - 2999 is shared events.
    3000 - 4999 is weapon events.
    5000+       is clientside events.
    """

    # New string-based type (eventlist.h)
    AE_EMPTY = 0
    AE_NPC_LEFTFOOT = 1
    AE_NPC_RIGHTFOOT = 2
    AE_NPC_BODYDROP_LIGHT = 3 
    AE_NPC_BODYDROP_HEAVY = 4
    AE_NPC_SWISHSOUND = 5
    AE_NPC_180TURN = 6
    AE_NPC_ITEM_PICKUP = 7
    AE_NPC_WEAPON_DROP = 8
    AE_NPC_WEAPON_SET_SEQUENCE_NAME = 9
    AE_NPC_WEAPON_SET_SEQUENCE_NUMBER = 10
    AE_NPC_WEAPON_SET_ACTIVITY = 11
    AE_NPC_HOLSTER = 11
    AE_NPC_DRAW = 12
    AE_NPC_WEAPON_FIRE = 13

    AE_CL_PLAYSOUND = 14
    AE_SV_PLAYSOUND = 15
    AE_CL_STOPSOUND = 16

    AE_START_SCRIPTED_EFFECT = 17
    AE_STOP_SCRIPTED_EFFECT = 18

    AE_CLIENT_EFFECT_ATTACH = 19

    AE_MUZZLEFLASH = 20
    AE_NPC_MUZZLEFLASH = 21

    AE_THUMPER_THUMP = 22
    AE_AMMOCRATE_PICKUP_AMMO = 23

    AE_NPC_RAGDOLL = 24
    AE_NPC_ADDGESTURE = 25
    AE_NPC_RESTARTGESTURE = 26
    AE_NPC_ATTACK_BROADCAST = 27
    AE_NPC_HURT_INTERACTION_PARTNER = 28
    AE_NPC_SET_INTERACTION_CANTDIE = 29

    AE_SV_DUSTTRAIL = 30
    AE_CL_CREATE_PARTICLE_EFFECT = 31
    AE_RAGDOLL = 32

    AE_CL_ENABLE_BODYGROUP = 33
    AE_CL_DISABLE_BODYGROUP = 34
    AE_CL_BODYGROUP_SET_VALUE = 35
    AE_CL_BODYGROUP_SET_VALUE_CMODEL_WPN = 36

    AE_WPN_PRIMARYATTACK = 37
    AE_WPN_INCREMENTAMMO = 38
    AE_WPN_HIDE = 39
    AE_WPN_UNHIDE = 40
    AE_WPN_PLAYWPNSOUND = 41

    AE_RD_ROBOT_POP_PANELS_OFF = 42

    AE_TAUNT_ENABLE_MOVE = 43
    AE_TAUNT_DISABLE_MOVE = 44

    # Alien Swarm+ events
    AE_ASW_FOOTSTEP = 45
    AE_MARINE_FOOTSTEP = 46
    AE_MARINE_RELOAD_SOUND_A = 47
    AE_MARINE_RELOAD_SOUND_B = 48
    AE_MARINE_RELOAD_SOUND_C = 49
    AE_REMOVE_CLIENT_AIM = 50

    AE_MELEE_DAMAGE = 51
    AE_MELEE_START_COLLISION_DAMAGE = 52
    AE_MELEE_STOP_COLLISION_DAMAGE = 53
    AE_SCREEN_SHAKE = 54
    AE_START_DETECTING_COMBO = 55
    AE_STOP_DETECTING_COMBO = 56
    AE_COMBO_TRANSITION = 57
    AE_ALLOW_MOVEMENT = 57
    AE_SKILL_EVENT = 59

    AE_TUG_INCAP = 60

    # Script events (scriptevent.h)
    SCRIPT_EVENT_DEAD           = 1000
    SCRIPT_EVENT_NOINTERRUPT    = 1001
    SCRIPT_EVENT_CANINTERRUPT   = 1002
    SCRIPT_EVENT_FIREEVENT      = 1003
    SCRIPT_EVENT_SOUND          = 1004
    SCRIPT_EVENT_SENTENCE       = 1005
    SCRIPT_EVENT_INAIR          = 1006
    SCRIPT_EVENT_ENDANIMATION   = 1007
    SCRIPT_EVENT_SOUND_VOICE    = 1008
    SCRIPT_EVENT_SENTENCE_RND1  = 1009
    SCRIPT_EVENT_NOT_DEAD       = 1010
    SCRIPT_EVENT_EMPHASIS       = 1011
    SCRIPT_EVENT_BODYGROUPON    = 1020
    SCRIPT_EVENT_BODYGROUPOFF   = 1021
    SCRIPT_EVENT_BODYGROUPTEMP  = 1022
    SCRIPT_EVENT_FIRE_INPUT     = 1100

    NPC_EVENT_BODYDROP_LIGHT    = 2001
    NPC_EVENT_BODYDROP_HEAVY    = 2002

    NPC_EVENT_SWISHSOUND        = 2010

    NPC_EVENT_180TURN           = 2020

    NPC_EVENT_ITEM_PICKUP                   = 2040
    NPC_EVENT_WEAPON_DROP                   = 2041
    NPC_EVENT_WEAPON_SET_SEQUENCE_NAME      = 2042
    NPC_EVENT_WEAPON_SET_SEQUENCE_NUMBER    = 2043
    NPC_EVENT_WEAPON_SET_ACTIVITY           = 2044

    NPC_EVENT_LEFTFOOT          = 2050
    NPC_EVENT_RIGHTFOOT         = 2051

    NPC_EVENT_OPEN_DOOR         = 2060

    EVENT_WEAPON_MELEE_HIT          = 3001
    EVENT_WEAPON_SMG1               = 3002
    EVENT_WEAPON_MELEE_SWISH        = 3003
    EVENT_WEAPON_SHOTGUN_FIRE       = 3004
    EVENT_WEAPON_THROW              = 3005
    EVENT_WEAPON_AR1                = 3006
    EVENT_WEAPON_AR2                = 3007
    EVENT_WEAPON_HMG1               = 3008
    EVENT_WEAPON_SMG2               = 3009
    EVENT_WEAPON_MISSILE_FIRE       = 3010
    EVENT_WEAPON_SNIPER_RIFLE_FIRE  = 3011
    EVENT_WEAPON_AR2_GRENADE        = 3012
    EVENT_WEAPON_THROW2             = 3013
    EVENT_WEAPON_PISTOL_FIRE        = 3014
    EVENT_WEAPON_RELOAD             = 3015
    EVENT_WEAPON_THROW3             = 3016
    EVENT_WEAPON_RELOAD_SOUND       = 3017
    EVENT_WEAPON_RELOAD_FILL_CLIP   = 3018
    EVENT_WEAPON_SMG1_BURST1        = 3101
    EVENT_WEAPON_SMG1_BURSTN        = 3102
    EVENT_WEAPON_AR2_ALTFIRE        = 3103

    EVENT_WEAPON_SEQUENCE_FINISHED  = 3900

    # Client-side events (cl_animevent.h)
    CL_EVENT_MUZZLEFLASH0 = 5001
    CL_EVENT_MUZZLEFLASH1 = 5011
    CL_EVENT_MUZZLEFLASH2 = 5021
    CL_EVENT_MUZZLEFLASH3 = 5031
    CL_EVENT_SPARK0 = 5002
    CL_EVENT_NPC_MUZZLEFLASH0 = 5003
    CL_EVENT_NPC_MUZZLEFLASH1 = 5013
    CL_EVENT_NPC_MUZZLEFLASH2 = 5023
    CL_EVENT_NPC_MUZZLEFLASH3 = 5033
    CL_EVENT_SOUND = 5004
    CL_EVENT_EJECTBRASS1 = 6001
    CL_EVENT_DISPATCHEFFECT0 = 9001
    CL_EVENT_DISPATCHEFFECT1 = 9011
    CL_EVENT_DISPATCHEFFECT2 = 9021
    CL_EVENT_DISPATCHEFFECT3 = 9031
    CL_EVENT_DISPATCHEFFECT4 = 9041
    CL_EVENT_DISPATCHEFFECT5 = 9051
    CL_EVENT_DISPATCHEFFECT6 = 9061
    CL_EVENT_DISPATCHEFFECT7 = 9071
    CL_EVENT_DISPATCHEFFECT8 = 9081
    CL_EVENT_DISPATCHEFFECT9 = 9091
    CL_EVENT_SPRITEGROUP_CREATE = 6002
    CL_EVENT_SPRITEGROUP_DESTROY = 6003
    CL_EVENT_FOOTSTEP_LEFT = 6004
    CL_EVENT_FOOTSTEP_RIGHT = 6005
    CL_EVENT_MFOOTSTEP_LEFT = 6006
    CL_EVENT_MFOOTSTEP_RIGHT = 6007
    CL_EVENT_MFOOTSTEP_LEFT_LOUD = 6008
    CL_EVENT_MFOOTSTEP_RIGHT_LOUD = 6009

    # These are defined directly as numbers, in
    # C_CSPlayer::FireEvent in the 2007 cstrike branch.
    CSS_FOOT_WATER_SPLASH = 7001
    CSS_FOOT_WATER_RIPPLE = 7002

    # A different set of foot impact events from
    # CSGO. Options are 'lfoot' or 'rfoot' (IK names)
    CSGO_FOOT_JUMP = 4001
    CSGO_FOOT_WALK = 4002


ANIM_EVENT_BY_INDEX = {
    event.value: event
    for event in AnimEvents
}  # type: Dict[int, AnimEvents]
ANIM_EVENT_BY_NAME = {
    event.name: event
    for event in AnimEvents
    # Don't save some that don't actually have official names.
    if event.value not in (4001, 4002, 7001, 7002)
}  # type: Dict[str, AnimEvents]

ST_PHY_HEADER = Struct('<iiil')


class Model:
    """Represents parts of Source models.

    This does not parse the animation or geometry data, only other metadata.
    """
    def __init__(self, filesystem: FileSystem, file: File):
        """Parse a model from a file."""
        self._file = file
        self._sys = filesystem
        self.version = 49

        self.phys_keyvalues = Property(None, [])
        with self._sys, self._file.open_bin() as f:
            self._load(f)

        path = PurePosixPath(file.path)
        try:
            phy_file = filesystem[str(path.with_suffix('.phy'))]
        except FileNotFoundError:
            pass
        else:
            with filesystem, phy_file.open_bin() as f:
                self._parse_phy(f, phy_file.path)

    def _load(self, f: BinaryIO) -> None:
        """Read data from the MDL file."""
        assert f.tell() == 0, "Doesn't begin at start?"
        if f.read(4) != b'IDST':
            raise ValueError('Not a model!')
        (
            self.version,
            name,
            file_len,
            # 4 bytes are unknown...
        ) = struct_read('i 4x 64s i', f)

        if not 44 <= self.version <= 49:
            raise ValueError('Unknown MDL version {}!'.format(self.version))

        self.name = name.rstrip(b'\0').decode('ascii')
        self.eye_pos = str_readvec(f)
        self.illum_pos = str_readvec(f)
        # Approx dimensions
        self.hull_min = str_readvec(f)
        self.hull_max = str_readvec(f)
        
        self.view_min = str_readvec(f)
        self.view_max = str_readvec(f)

        # Break up the reading a bit to limit the stack size.
        (
            flags,

            bone_count,
            bone_off,

            bone_controller_count, bone_controller_off,

            hitbox_count, hitbox_off,
            anim_count, anim_off,
            sequence_count, sequence_off,
        ) = struct_read('11I', f)

        self.flags = Flags(flags)

        (
            activitylistversion, eventsindexed,

            texture_count, texture_offset,
            cdmat_count, cdmat_offset,
            
            skinref_count,  # Number of skin "groups"
            skin_count,   # Number of model skins.
            skinref_ind,  # Location of skins reference table.

            # The number of $body in the model (mstudiobodyparts_t).
            bodypart_count, bodypart_offset,
            attachment_count, attachment_offset,
        ) = struct_read('13i', f)

        (
            localnode_count,
            localnode_index,
            localnode_name_index,
         
            # mstudioflexdesc_t
            flexdesc_count,
            flexdesc_index,
         
            # mstudioflexcontroller_t
            flexcontroller_count,
            flexcontroller_index,
         
            # mstudioflexrule_t
            flexrules_count,
            flexrules_index,
         
            # IK probably refers to inverse kinematics
            # mstudioikchain_t
            ikchain_count,
            ikchain_index,
         
            # Information about any "mouth" on the model for speech animation
            # More than one sounds pretty creepy.
            # mstudiomouth_t
            mouths_count, 
            mouths_index,
         
            # mstudioposeparamdesc_t
            localposeparam_count,
            localposeparam_index,
        ) = struct_read('15I', f)

        # VDC:
        # For anyone trying to follow along, as of this writing,
        # the next "surfaceprop_index" value is at position 0x0134 (308)
        # from the start of the file.
        assert f.tell() == 308, 'Offset wrong? {} != 308 {}'.format(f.tell(), f)

        (
            # Surface property value (single null-terminated string)
            surfaceprop_index,
         
            # Unusual: In this one index comes first, then count.
            # Key-value data is a series of strings. If you can't find
            # what you're interested in, check the associated PHY file as well.
            keyvalue_index,
            keyvalue_count,	
         
            # More inverse-kinematics
            # mstudioiklock_t
            iklock_count,
            iklock_index,
        ) = struct_read('5I', f)

        (
            self.mass,  # Mass of object (float)
            self.contents,  # ??

            # Other models can be referenced for re-used sequences and
            # animations
            # (See also: The $includemodel QC option.)
            # mstudiomodelgroup_t
            includemodel_count,
            includemodel_index,

            # In-engine, this is a pointer to the combined version of this +
            # included models. In the file it's useless.
            virtualModel,

            # mstudioanimblock_t
            animblocks_name_index,
            animblocks_count,
            animblocks_index,

            animblockModel,  # Placeholder for mutable-void*

            # Points to a series of bytes?
            bonetablename_index,

            vertex_base,  # Placeholder for void*
            offset_base,  # Placeholder for void*
        ) = struct_read('f 11I', f)

        (
            # Used with $constantdirectionallight from the QC
            # Model should have flag #13 set if enabled
            directionaldotproduct,  # byte

            # Preferred rather than clamped
            rootLod,  # byte

            # 0 means any allowed, N means Lod 0 -> (N-1)
            self.numAllowedRootLods,  # byte

            #unknown byte;
            #unknown int;

            # mstudioflexcontrollerui_t
            flexcontrollerui_count,
            flexcontrollerui_index,
        ) = struct_read('3b 5x 2I', f)

        # Build CDMaterials data
        f.seek(cdmat_offset)
        self.cdmaterials = read_offset_array(f, cdmat_count)
        
        for ind, cdmat in enumerate(self.cdmaterials):
            cdmat = cdmat.replace('\\', '/').lstrip('/')
            if cdmat and cdmat[-1:] != '/':
                cdmat += '/'
            self.cdmaterials[ind] = cdmat
        
        # Build texture data
        f.seek(texture_offset)
        textures = [None] * texture_count  # type: List[Tuple[str, int, int]]
        tex_temp = [None] * texture_count  # type: List[Tuple[int, Tuple[int, int, int]]]
        for tex_ind in range(texture_count):
            tex_temp[tex_ind] = (
                f.tell(),
                # Texture data:
                # int: offset to the string, from start of struct.
                # int: flags - appears to solely indicate 'teeth' materials...
                # int: used, whatever that means.
                # 4 unused bytes.
                # 2 4-byte pointers in studiomdl to the material class, for
                #      server and client - shouldn't be in the file...
                # 40 bytes of unused space (for expansion...)
                struct_read('iii 4x 8x 40x', f)
            )
        for tex_ind, (offset, data) in enumerate(tex_temp):
            name_offset, flags, used = data
            textures[tex_ind] = (
                read_nullstr(f, offset + name_offset),
                flags,
                used,
            )

        # Now parse through the family table, to match skins to textures.
        f.seek(skinref_ind)
        ref_data = f.read(2 * skinref_count * skin_count)
        self.skins = [None] * skin_count  # type: List[List[str]]
        skin_group = Struct('<{}H'.format(skinref_count))
        offset = 0
        for ind in range(skin_count):
            self.skins[ind] = [
                textures[i][0].replace('\\', '/').lstrip('/')
                for i in skin_group.unpack_from(ref_data, offset)
            ]
            offset += skin_group.size

        # If models have folders, add those folders onto cdmaterials.
        for tex, flags, used in textures:
            tex = tex.replace('\\', '/')
            if '/' in tex:
                folder = tex.rsplit('/', 1)[0]
                if folder not in self.cdmaterials:
                    self.cdmaterials.append(folder)

        # All models fallback to checking the texture at a root folder.
        if '' not in self.cdmaterials:
            self.cdmaterials.append('')

        f.seek(surfaceprop_index)
        self.surfaceprop = read_nullstr(f)

        if keyvalue_count:
            self.keyvalues = read_nullstr(f, keyvalue_index)
        else:
            self.keyvalues = ''

        f.seek(includemodel_index)
        self.included_models = [None] * includemodel_count  # type: List[IncludedMDL]
        for i in range(includemodel_count):
            pos = f.tell()
            # This is two offsets from the start of the structures.
            lbl_pos, filename_pos = struct_read('II', f)
            self.included_models[i] = IncludedMDL(
                read_nullstr(f, pos + lbl_pos) if lbl_pos else '',
                read_nullstr(f, pos + filename_pos) if filename_pos else '',
            )
            # Then return to after that struct - 4 bytes * 2.
            f.seek(pos + 4 * 2)

        f.seek(sequence_off)
        self.sequences = self._read_sequences(f, sequence_count)

        f.seek(bodypart_offset)
        self._cull_skins_table(f, bodypart_count)

    @staticmethod
    def _read_sequences(f: BinaryIO, count: int) -> List[MDLSequence]:
        """Split this off to decrease stack in main parse method."""
        sequences = [None] * count  # type: List[MDLSequence]
        for i in range(count):
            start_pos = f.tell()
            (
                base_ptr,
                label_pos,
                act_name_pos,
                flags,
                _,  # Seems to be a pointer.
                act_weight,
                event_count,
                event_pos,
            ) = struct_read('8i', f)
            bbox_min = str_readvec(f)
            bbox_max = str_readvec(f)

            # Skip 20 ints, 9 floats to get to keyvalues = 29*4 bytes
            # Then 8 unused ints.
            (
                keyvalue_pos,
                keyvalue_size,
            ) = struct_read('116xii32x', f)
            end_pos = f.tell()

            f.seek(start_pos + event_pos)
            events = [None] * event_count  # type: List[SeqEvent]
            for j in range(event_count):
                event_start = f.tell()
                (
                    event_cycle,
                    event_index,
                    event_flags,
                    event_options,
                    event_nameloc,
                ) = struct_read('fii64si', f)
                event_end = f.tell()

                # There are two event systems.
                if event_flags == 1 << 10:
                    # New system, name in the file.
                    event_name = read_nullstr(f, event_start + event_nameloc)
                    if event_name.isdigit():
                        try:
                            event_type = ANIM_EVENT_BY_INDEX[int(event_name)]
                        except KeyError:
                            raise ValueError('Unknown event index!')
                    else:
                        try:
                            event_type = ANIM_EVENT_BY_NAME[event_name]
                        except KeyError:
                            # NPC-specific events, declared dynamically.
                            event_type = event_name
                else:
                    # Old system, index.
                    try:
                        event_type = ANIM_EVENT_BY_INDEX[event_index]
                    except KeyError:
                        # raise ValueError('Unknown event index!')
                        print('Unknown: ', event_index, event_options.rstrip(b'\0'))
                        continue

                f.seek(event_end)
                events[j] = SeqEvent(
                    type=event_type,
                    cycle=event_cycle,
                    options=event_options.rstrip(b'\0').decode('ascii')
                )

            if keyvalue_size:
                keyvalues = read_nullstr(f, start_pos + keyvalue_pos)
            else:
                keyvalues = ''

            sequences[i] = MDLSequence(
                label=read_nullstr(f, start_pos + label_pos),
                act_name=read_nullstr(f, start_pos + act_name_pos),
                flags=flags,
                act_weight=act_weight,
                events=events,
                bbox_min=bbox_min,
                bbox_max=bbox_max,
                keyvalues=keyvalues,
            )

            f.seek(end_pos)

        return sequences

    def _cull_skins_table(self, f: BinaryIO, body_count: int) -> None:
        """Fix the table of used skins to correspond to those actually used.

        StudioMDL is rather messy, and adds many extra columns that are not used
        on the actual model.
        We're following  mstudiobodyparts_t -> mstudiomodel_t -> mstudiomesh_t -> material.
        """
        used_inds = set()

        # Iterate through bodygroups.
        for body_ind in range(body_count):
            body_start = f.tell()
            (
                body_name_off,  # Offset to find the bodygroup name
                model_count,  # Number of models in this group
                base,  # Unknown
                model_off,
            ) = struct_read('iiii', f)
            body_end = f.tell()

            f.seek(body_start + model_off)
            for model_ind in range(model_count):
                model_start = f.tell()
                (
                    mdl_name,
                    mdl_type,
                    bound_radius,
                    mesh_count,
                    mesh_off,
                    num_verts,
                    vert_off,
                    tangent_off,
                    attach_count,
                    attach_ind,
                    eyeball_count,
                    eyeball_ind,
                    # Two void* pointers,
                    # 32 empty bytes
                ) = struct_read('64s i f 9i 8x 32x', f)
                model_end = f.tell()

                f.seek(model_start + mesh_off)
                for mesh_ind in range(mesh_count):
                    (
                        material,
                        mesh_model_ind,
                        mesh_vert_count,
                        mesh_vert_off,
                        mesh_flex_count,
                        mesh_flex_ind,
                        mesh_mat_type,
                        mesh_mat_param,
                        mesh_id,
                        mesh_cent_x,
                        mesh_cent_y,
                        mesh_cent_z,
                        # Void pointer
                        # Array of LOD vertex counts ints, 8 of them
                        # 8 unused int spaces.
                    ) = struct_read('9i 3f 4x 32x 32x', f)
                    used_inds.add(material)

                f.seek(model_end)
            f.seek(body_end)

        for skin_ind, tex in enumerate(self.skins):
            self.skins[skin_ind] = [tex[i] for i in used_inds]

    def _parse_phy(self, f: BinaryIO, filename: str) -> None:
        """Parse the physics data file, if present.
        """
        [
            size,
            header_id,
            solid_count,
            checksum,
        ] = ST_PHY_HEADER.unpack(f.read(ST_PHY_HEADER.size))
        f.read(size - ST_PHY_HEADER.size)  # If the header is larger ever.
        for solid in range(solid_count):
            [solid_size] = struct_read('i', f)
            f.read(solid_size)  # Skip the header.
        self.phys_keyvalues = Property.parse(
            read_nullstr(f),
            filename + ":keyvalues",
            allow_escapes=False,
            single_line=True,
        )

    def iter_textures(self, skins: Iterable[int]=None) -> Iterator[str]:
        """Yield textures used by this model.

        Skins if given should be a set of skin indexes, which constrains the
        list. This looks up in the filesystem to determine which CDMaterials
        folder to use, if any.
        """

        if skins:
            paths = set()
            for ind in skins:
                try:
                    paths.update(self.skins[ind])
                except IndexError:
                    # Default to skin 0.
                    paths.update(self.skins[0])
        else:
            paths = {
                tex
                for texgroup in self.skins
                for tex in texgroup
            }

        with self._sys:
            for tex in paths:
                for folder in self.cdmaterials:
                    full = str(PurePosixPath('materials', folder, tex).with_suffix('.vmt'))
                    if full in self._sys:
                        yield full
                        break

    def find_sounds(self) -> Iterator[str]:
        """Yield all sounds used by animations.

        """
        sound_events = [
            AnimEvents.AE_CL_PLAYSOUND,
            AnimEvents.AE_SV_PLAYSOUND,
            AnimEvents.SCRIPT_EVENT_SOUND,
            AnimEvents.SCRIPT_EVENT_SOUND_VOICE,
        ]
        footstep_events = [
            AnimEvents.AE_NPC_LEFTFOOT,
            AnimEvents.AE_NPC_RIGHTFOOT,
        ]

        for seq in self.sequences:
            for event in seq.events:
                if event.type in sound_events:
                    yield event.options
                if event.type in footstep_events:
                    npc = event.options or "NPC_CombineS"
                    yield npc + ".RunFootstepLeft"
                    yield npc + ".RunFootstepRight"
                    yield npc + ".FootstepLeft"
                    yield npc + ".FootstepRight"
