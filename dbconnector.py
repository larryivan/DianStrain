from models import BasicInfo, EcologyData, MorphologyData, GenomicsData, PhysiologyData, db
from datetime import datetime, timedelta


class db_connector:
    def __init__(self, database='sqlite:///instance/db/genebase.db'):
        self.database = database

    def add_to_db(self, dt):
        session = db.session()
        try:
            # Check if the record already exists
            existing_record = session.query(BasicInfo).filter_by(basic_info_id=dt['basic_info_id']).first()
            if existing_record:
                raise ValueError(f"Record with basic_info_id {dt['basic_info_id']} already exists.")

            basic_info = BasicInfo(
                basic_info_id=dt['basic_info_id'], genus=dt['genus'], species=dt['species'],
                classification_status=dt['classification_status'], preservation_date=dt['preservation_date'],
                chinese_name=dt['chinese_name'], is_type_strain=dt['is_type_strain'],
                preservation_unit=dt['preservation_unit'],
                preservation_method=dt['preservation_method'], preserver=dt['preserver'],
                preservation_notes=dt['preservation_notes'], contact_info=dt['contact_info']
            )
            session.add(basic_info)

            ecology_data = EcologyData(
                basic_info_id=dt['basic_info_id'], location_name=dt['location_name'],
                habitat=dt['habitat'],
                coordinates=dt['coordinates'], sampling_date=dt['sampling_date'],
                sample_type=dt['sample_type'],
                temperature=dt['temperature'], oxygen_requirement=dt['oxygen_requirement'],
                sampler=dt['sampler']
            )
            session.add(ecology_data)

            morphology_data = MorphologyData(
                basic_info_id=dt['basic_info_id'], description=dt['description'],
                colony_color=dt['colony_color'], colony_shape=dt['colony_shape'], colony_edge=dt['colony_edge'],
                colony_surface=dt['colony_surface'], colony_size=dt['colony_size'], colony_texture=dt['colony_texture'],
                motility=dt['motility'], spore_shape=dt['spore_shape'],
                spore_staining_reaction=dt['spore_staining_reaction'],
                observation_medium=dt['observation_medium'],
                observation_conditions=dt['observation_conditions']
            )
            session.add(morphology_data)

            genomics_data = GenomicsData(
                basic_info_id=dt['basic_info_id'], sequencing_method=dt['sequencing_method'],
                assembly_method=dt['assembly_method'],
                annotation_method=dt['annotation_method'], genome_size=dt['genome_size'], gc_content=dt['gc_content'],
                n50=dt['n50'], contig_count=dt['contig_count'], scaffold_count=dt['scaffold_count'],
                trna_count=dt['trna_count'],
                rrna_count=dt['rrna_count']
            )
            session.add(genomics_data)

            physiology_data = PhysiologyData(
                basic_info_id=dt['basic_info_id'], nicotine_degradation=dt['nicotine_degradation'],
                cellulase=dt['cellulase'],
                acidic_protease=dt['acidic_protease'], lignin_degrading_enzymes=dt['lignin_degrading_enzymes']
            )
            session.add(physiology_data)

            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            raise e
        finally:
            session.close()

    def getID(self):
        session = db.session()
        try:
            ids = session.query(BasicInfo.basic_info_id).all()
            return [id[0] for id in ids]
        finally:
            session.close()

    def delete(self, basic_info_id):
        session = db.session()
        try:
            session.query(BasicInfo).filter(BasicInfo.basic_info_id == basic_info_id).delete()
            session.query(EcologyData).filter(EcologyData.basic_info_id == basic_info_id).delete()
            session.query(MorphologyData).filter(MorphologyData.basic_info_id == basic_info_id).delete()
            session.query(GenomicsData).filter(GenomicsData.basic_info_id == basic_info_id).delete()
            session.query(PhysiologyData).filter(PhysiologyData.basic_info_id == basic_info_id).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def getdata(self, basic_info_id):
        session = db.session()
        try:
            basic_info = session.query(BasicInfo).filter(BasicInfo.basic_info_id == basic_info_id).first()
            ecology_data = session.query(EcologyData).filter(EcologyData.basic_info_id == basic_info_id).first()
            morphology_data = session.query(MorphologyData).filter(
                MorphologyData.basic_info_id == basic_info_id).first()
            genomics_data = session.query(GenomicsData).filter(GenomicsData.basic_info_id == basic_info_id).first()
            physiology_data = session.query(PhysiologyData).filter(
                PhysiologyData.basic_info_id == basic_info_id).first()

            result = {}
            if basic_info:
                result.update(basic_info.__dict__)
            if ecology_data:
                result.update(ecology_data.__dict__)
            if morphology_data:
                result.update(morphology_data.__dict__)
            if genomics_data:
                result.update(genomics_data.__dict__)
            if physiology_data:
                result.update(physiology_data.__dict__)

            result.pop('_sa_instance_state', None)

            return result
        finally:
            session.close()

    def get_statistics(self):
        session = db.session()
        try:
            # 获取所有信息的总数目
            total_count = session.query(BasicInfo).count()

            # 计算出一年前的日期
            one_year_ago = datetime.now() - timedelta(days=365)

            # 最近一年内保存的数目
            recent_preservation_count = session.query(BasicInfo).filter(
                BasicInfo.preservation_date >= one_year_ago.strftime('%Y-%m-%d')
            ).count()

            # 最近一年内采样的数目
            recent_sampling_count = session.query(EcologyData).filter(
                EcologyData.sampling_date >= one_year_ago.strftime('%Y-%m-%d')
            ).count()

            return {
                "total_count": total_count,
                "recent_preservation_count": recent_preservation_count,
                "recent_sampling_count": recent_sampling_count
            }
        finally:
            session.close()

    def update(self, dt):
        session = db.session()
        try:
            print("Starting database update process...")
        
            # 更新 BasicInfo 表
            print(f"Querying BasicInfo with basic_info_id = {dt['basic_info_id']}...")
            basic_info = session.query(BasicInfo).filter(BasicInfo.basic_info_id == dt['basic_info_id']).first()
            if basic_info:
                print("Found BasicInfo record. Updating fields...")
                for key, value in dt.items():
                    if hasattr(basic_info, key):
                        setattr(basic_info, key, value)
                        print(f"Updated BasicInfo field '{key}' to '{value}'.")
                session.add(basic_info)
            else:
                print("No BasicInfo record found.")

            # 更新 EcologyData 表
            print(f"Querying EcologyData with basic_info_id = {dt['basic_info_id']}...")
            ecology_data = session.query(EcologyData).filter(EcologyData.basic_info_id == dt['basic_info_id']).first()
            if ecology_data:
                print("Found EcologyData record. Updating fields...")
                for key, value in dt.items():
                    if hasattr(ecology_data, key):
                        setattr(ecology_data, key, value)
                        print(f"Updated EcologyData field '{key}' to '{value}'.")
                session.add(ecology_data)
            else:
                print("No EcologyData record found.")

            # 更新 MorphologyData 表
            print(f"Querying MorphologyData with basic_info_id = {dt['basic_info_id']}...")
            morphology_data = session.query(MorphologyData).filter(
                MorphologyData.basic_info_id == dt['basic_info_id']).first()
            if morphology_data:
                print("Found MorphologyData record. Updating fields...")
                for key, value in dt.items():
                    if hasattr(morphology_data, key):
                        setattr(morphology_data, key, value)
                        print(f"Updated MorphologyData field '{key}' to '{value}'.")
                session.add(morphology_data)
            else:
                print("No MorphologyData record found.")

            # 更新 GenomicsData 表
            print(f"Querying GenomicsData with basic_info_id = {dt['basic_info_id']}...")
            genomics_data = session.query(GenomicsData).filter(
                GenomicsData.basic_info_id == dt['basic_info_id']).first()
            if genomics_data:
                print("Found GenomicsData record. Updating fields...")
                for key, value in dt.items():
                    if hasattr(genomics_data, key):
                        setattr(genomics_data, key, value)
                        print(f"Updated GenomicsData field '{key}' to '{value}'.")
                session.add(genomics_data)
            else:
                print("No GenomicsData record found.")

            # 更新 PhysiologyData 表
            print(f"Querying PhysiologyData with basic_info_id = {dt['basic_info_id']}...")
            physiology_data = session.query(PhysiologyData).filter(
                PhysiologyData.basic_info_id == dt['basic_info_id']).first()
            if physiology_data:
                print("Found PhysiologyData record. Updating fields...")
                for key, value in dt.items():
                    if hasattr(physiology_data, key):
                        setattr(physiology_data, key, value)
                        print(f"Updated PhysiologyData field '{key}' to '{value}'.")
                session.add(physiology_data)
            else:
                print("No PhysiologyData record found.")

            # 提交事务
            print("Committing the transaction...")
            session.commit()
            print("Database update process completed successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            print("Rolling back the transaction...")
            session.rollback()
            raise e

        finally:
            print("Closing the database session...")
            session.close()
