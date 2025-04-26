import os
from sqlalchemy import create_engine, Column, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BasicInfo(Base):
    __tablename__ = 'BasicInfo'
    basic_info_id = Column(String(20), primary_key=True, nullable=False)
    genus = Column(String, nullable=False)
    species = Column(String, nullable=False)
    classification_status = Column(String, nullable=True)
    preservation_date = Column(String, nullable=True)
    chinese_name = Column(String, nullable=True)
    is_type_strain = Column(String, nullable=True)
    preservation_unit = Column(String, nullable=True)
    preservation_method = Column(String, nullable=True)
    preserver = Column(String, nullable=True)
    preservation_notes = Column(Text, nullable=True)
    contact_info = Column(String, nullable=True)


class EcologyData(Base):
    __tablename__ = 'EcologyData'
    basic_info_id = Column(String(20), ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    location_name = Column(String, nullable=True)
    habitat = Column(String, nullable=True)
    coordinates = Column(String, nullable=True)
    sampling_date = Column(String, nullable=True)
    sample_type = Column(String, nullable=True)
    temperature = Column(String, nullable=True)
    oxygen_requirement = Column(String, nullable=True)
    sampler = Column(String, nullable=True)


class MorphologyData(Base):
    __tablename__ = 'MorphologyData'
    basic_info_id = Column(String(20), ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    description = Column(Text, nullable=True)
    colony_color = Column(String, nullable=True)
    colony_shape = Column(String, nullable=True)
    colony_edge = Column(String, nullable=True)
    colony_surface = Column(String, nullable=True)
    colony_size = Column(String, nullable=True)
    colony_texture = Column(String, nullable=True)
    motility = Column(String, nullable=True)
    spore_shape = Column(String, nullable=True)
    spore_staining_reaction = Column(String, nullable=True)
    observation_medium = Column(Text, nullable=True)
    observation_conditions = Column(Text, nullable=True)


class GenomicsData(Base):
    __tablename__ = 'GenomicsData'
    basic_info_id = Column(String(20), ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    sequencing_method = Column(String, nullable=True)
    assembly_method = Column(String, nullable=True)
    annotation_method = Column(String, nullable=True)
    genome_size = Column(String, nullable=True)
    gc_content = Column(String, nullable=True)
    n50 = Column(String, nullable=True)
    contig_count = Column(String, nullable=True)
    scaffold_count = Column(String, nullable=True)
    trna_count = Column(String, nullable=True)
    rrna_count = Column(String, nullable=True)


class PhysiologyData(Base):
    __tablename__ = 'PhysiologyData'
    basic_info_id = Column(String(20), ForeignKey('BasicInfo.basic_info_id'), primary_key=True, nullable=False)
    nicotine_degradation = Column(String, nullable=True)
    cellulase = Column(String, nullable=True)
    acidic_protease = Column(String, nullable=True)
    lignin_degrading_enzymes = Column(String, nullable=True)


def create_database(database='sqlite:///instance/db/genebase.db'):
    os.makedirs('instance/db', exist_ok=True)
    engine = create_engine(database)
    Base.metadata.create_all(engine)
    print("Database created successfully!")


if __name__ == '__main__':
    create_database()
