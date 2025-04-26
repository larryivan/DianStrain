from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BasicInfo(db.Model):
    __tablename__ = 'BasicInfo'
    basic_info_id = db.Column(db.String(20), primary_key=True, nullable=False)
    genus = db.Column(db.String(50), index=True)
    species = db.Column(db.String(50), index=True)
    classification_status = db.Column(db.String(50), index=True)
    preservation_date = db.Column(db.String(20), index=True)
    chinese_name = db.Column(db.String(50), index=True)
    is_type_strain = db.Column(db.String(10))
    preservation_unit = db.Column(db.String(50))
    preservation_method = db.Column(db.String(50))
    preserver = db.Column(db.String(20))
    preservation_notes = db.Column(db.Text)
    contact_info = db.Column(db.String(50))

class EcologyData(db.Model):
    __tablename__ = 'EcologyData'
    basic_info_id = db.Column(db.String(20), db.ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    location_name = db.Column(db.String, nullable=True)
    habitat = db.Column(db.String, nullable=True)
    coordinates = db.Column(db.String, nullable=True)
    sampling_date = db.Column(db.String, nullable=True)
    sample_type = db.Column(db.String, nullable=True)
    temperature = db.Column(db.String, nullable=True)
    oxygen_requirement = db.Column(db.String, nullable=True)
    sampler = db.Column(db.String, nullable=True)

class MorphologyData(db.Model):
    __tablename__ = 'MorphologyData'
    basic_info_id = db.Column(db.String(20), db.ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    colony_color = db.Column(db.String, nullable=True)
    colony_shape = db.Column(db.String, nullable=True)
    colony_edge = db.Column(db.String, nullable=True)
    colony_surface = db.Column(db.String, nullable=True)
    colony_size = db.Column(db.String, nullable=True)
    colony_texture = db.Column(db.String, nullable=True)
    motility = db.Column(db.String, nullable=True)
    spore_shape = db.Column(db.String, nullable=True)
    spore_staining_reaction = db.Column(db.String, nullable=True)
    observation_medium = db.Column(db.Text, nullable=True)
    observation_conditions = db.Column(db.Text, nullable=True)

class GenomicsData(db.Model):
    __tablename__ = 'GenomicsData'
    basic_info_id = db.Column(db.String(20), db.ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    sequencing_method = db.Column(db.String, nullable=True)
    assembly_method = db.Column(db.String, nullable=True)
    annotation_method = db.Column(db.String, nullable=True)
    genome_size = db.Column(db.String, nullable=True)
    gc_content = db.Column(db.String, nullable=True)
    n50 = db.Column(db.String, nullable=True)
    contig_count = db.Column(db.String, nullable=True)
    scaffold_count = db.Column(db.String, nullable=True)
    trna_count = db.Column(db.String, nullable=True)
    rrna_count = db.Column(db.String, nullable=True)

class PhysiologyData(db.Model):
    __tablename__ = 'PhysiologyData'
    basic_info_id = db.Column(db.String(20), db.ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    nicotine_degradation = db.Column(db.String, nullable=True)
    cellulase = db.Column(db.String, nullable=True)
    acidic_protease = db.Column(db.String, nullable=True)
    lignin_degrading_enzymes = db.Column(db.String, nullable=True)
