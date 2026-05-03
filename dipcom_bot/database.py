import os
import logging
from datetime import date
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
import aiomysql
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'bot_admin'),
            'password': os.getenv('DB_PASSWORD', 'SecurePass123'),
            'db': os.getenv('DB_NAME', 'resource_bot'),
            'charset': 'utf8mb4',
            'cursorclass': aiomysql.DictCursor,
            'autocommit': False,
        }

    async def init_db(self):
        try:
            self.pool = await aiomysql.create_pool(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                db=self.db_config['db'],
                charset=self.db_config['charset'],
                cursorclass=self.db_config['cursorclass'],
                autocommit=self.db_config['autocommit'],
                maxsize=10,
            )
            logger.info('MySQL database pool initialized successfully')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize MySQL database: {e}')
            raise

    async def close_db(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info('MySQL database pool closed')

    @asynccontextmanager
    async def get_connection(self):
        async with self.pool.acquire() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f'Database error: {e}')
                raise

    async def _fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchone()

    async def _fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchall()

    async def _execute(self, query: str, params: tuple = None) -> int:
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return cursor.rowcount

    # User methods
    async def register_user(self, user_id: int, full_name: str, father_name: str,
                           phone_number: str = None, username: str = None, status: str = 'pending') -> bool:
        try:
            await self._execute(
                '''
                    INSERT INTO users (user_id, full_name, father_name, phone_number, username, status, registered_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), father_name = VALUES(father_name),
                        phone_number = VALUES(phone_number), username = VALUES(username), status = VALUES(status)
                ''',
                (user_id, full_name, father_name, phone_number, username, status)
            )
            return True
        except Exception as e:
            logger.error(f'Error registering user: {e}')
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            return await self._fetchone('SELECT * FROM users WHERE user_id = %s', (user_id,))
        except Exception as e:
            logger.error(f'Error getting user: {e}')
            return None

    async def update_user_status(self, user_id: int, status: str) -> bool:
        try:
            await self._execute(
                '''
                    UPDATE users
                    SET status = %s,
                        enrolled_at = CASE WHEN %s = 'enrolled' THEN CURRENT_TIMESTAMP ELSE enrolled_at END
                    WHERE user_id = %s
                ''',
                (status, status, user_id)
            )
            return True
        except Exception as e:
            logger.error(f'Error updating user status: {e}')
            return False

    async def get_all_users(self, status: str = None) -> List[Dict]:
        try:
            if status:
                return await self._fetchall('SELECT * FROM users WHERE status = %s ORDER BY registered_at DESC', (status,))
            return await self._fetchall('SELECT * FROM users ORDER BY registered_at DESC')
        except Exception as e:
            logger.error(f'Error getting users: {e}')
            return []

    # Module methods
    async def add_module(self, module_name: str, created_by: int) -> bool:
        try:
            await self._execute(
                'INSERT INTO modules (module_name, created_at, created_by) VALUES (%s, CURRENT_TIMESTAMP, %s)',
                (module_name, created_by)
            )
            return True
        except Exception as e:
            if 'Duplicate entry' in str(e):
                logger.warning(f"Module '{module_name}' already exists")
                return False
            logger.error(f'Error adding module: {e}')
            return False

    async def get_modules(self) -> List[Dict]:
        try:
            return await self._fetchall('SELECT * FROM modules ORDER BY module_name')
        except Exception as e:
            logger.error(f'Error getting modules: {e}')
            return []

    async def get_module(self, module_id: int) -> Optional[Dict]:
        try:
            return await self._fetchone('SELECT * FROM modules WHERE id = %s', (module_id,))
        except Exception as e:
            logger.error(f'Error getting module: {e}')
            return None

    async def get_module_by_name(self, module_name: str) -> Optional[Dict]:
        try:
            return await self._fetchone('SELECT * FROM modules WHERE module_name = %s', (module_name,))
        except Exception as e:
            logger.error(f'Error getting module by name: {e}')
            return None

    async def delete_module(self, module_id: int) -> bool:
        try:
            await self._execute('DELETE FROM modules WHERE id = %s', (module_id,))
            return True
        except Exception as e:
            logger.error(f'Error deleting module: {e}')
            return False

    # Resource methods
    async def add_resource(self, module_id: int, file_id: str, file_name: str,
                          file_type: str, uploaded_by: int) -> bool:
        try:
            await self._execute(
                '''
                    INSERT INTO resources (module_id, file_id, file_name, file_type, uploaded_by, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ''',
                (module_id, file_id, file_name, file_type, uploaded_by)
            )
            return True
        except Exception as e:
            logger.error(f'Error adding resource: {e}')
            return False

    async def get_module_resources(self, module_id: int) -> List[Dict]:
        try:
            return await self._fetchall('SELECT * FROM resources WHERE module_id = %s ORDER BY uploaded_at DESC', (module_id,))
        except Exception as e:
            logger.error(f'Error getting module resources: {e}')
            return []

    async def get_resource(self, resource_id: int) -> Optional[Dict]:
        try:
            return await self._fetchone('SELECT * FROM resources WHERE id = %s', (resource_id,))
        except Exception as e:
            logger.error(f'Error getting resource: {e}')
            return None

    async def delete_resource(self, resource_id: int) -> bool:
        try:
            await self._execute('DELETE FROM resources WHERE id = %s', (resource_id,))
            return True
        except Exception as e:
            logger.error(f'Error deleting resource: {e}')
            return False

    async def get_followup_survey(self, survey_id: str = 'job_followup') -> Optional[Dict]:
        try:
            return await self._fetchone('SELECT * FROM surveys_survey WHERE id = %s', (survey_id,))
        except Exception as e:
            logger.error(f'Error getting follow-up survey: {e}')
            return None

    async def ensure_followup_survey(self, question: str = None, survey_id: str = 'job_followup') -> dict:
        current = await self.get_followup_survey(survey_id)
        if current:
            if question is not None and current.get('question') != question:
                await self.update_followup_survey_question(question, survey_id)
                current = await self.get_followup_survey(survey_id)
            return current

        if question is None:
            question = 'Have you found a job after graduation? Please answer Yes or No.'

        await self._execute(
            '''
                INSERT INTO surveys_survey (id, question, survey_type, last_sent, response_yes, response_no)
                VALUES (%s, %s, %s, CURRENT_DATE, 0, 0)
            ''',
            (survey_id, question, 'yes_no')
        )

        return {
            'id': survey_id,
            'question': question,
            'survey_type': 'yes_no',
            'last_sent': date.today().isoformat(),
            'response_yes': 0,
            'response_no': 0,
        }

    async def update_followup_survey_question(self, question: str, survey_id: str = 'job_followup') -> Optional[Dict]:
        try:
            await self._execute('UPDATE surveys_survey SET question = %s WHERE id = %s', (question, survey_id))
            return await self.get_followup_survey(survey_id)
        except Exception as e:
            logger.error(f'Error updating follow-up survey question: {e}')
            return None

    async def update_followup_survey_last_sent(self, survey_id: str = 'job_followup') -> bool:
        try:
            await self._execute('UPDATE surveys_survey SET last_sent = CURRENT_DATE WHERE id = %s', (survey_id,))
            return True
        except Exception as e:
            logger.error(f'Error updating follow-up survey last_sent: {e}')
            return False

    async def get_graduated_students(self) -> List[Dict]:
        try:
            return await self._fetchall(
                'SELECT id, telegram_user_id, name FROM students_student WHERE graduated = 1 AND telegram_user_id IS NOT NULL'
            )
        except Exception as e:
            logger.error(f'Error getting graduated students: {e}')
            return []

    async def delete_student_by_phone(self, phone_number: str) -> bool:
        try:
            deleted = await self._execute('DELETE FROM students_student WHERE phone = %s', (phone_number,))
            return deleted > 0
        except Exception as e:
            logger.error(f'Error deleting student by phone: {e}')
            return False

    async def record_employment_response(self, student_id: str, survey_id: str, is_employed: bool, phone_number: str = None) -> bool:
        try:
            existing = await self._fetchone(
                'SELECT id, is_employed FROM students_employmentcheckin WHERE student_id = %s AND survey_id = %s',
                (student_id, survey_id)
            )

            if existing:
                previous_answer = bool(existing['is_employed'])
                if previous_answer == is_employed:
                    return True

                await self._execute(
                    'UPDATE students_employmentcheckin SET is_employed = %s, checked_at = CURRENT_TIMESTAMP WHERE id = %s',
                    (int(is_employed), existing['id'])
                )

                if is_employed:
                    await self._execute('UPDATE surveys_survey SET response_yes = response_yes + 1, response_no = response_no - 1 WHERE id = %s', (survey_id,))
                else:
                    await self._execute('UPDATE surveys_survey SET response_no = response_no + 1, response_yes = response_yes - 1 WHERE id = %s', (survey_id,))

                if phone_number:
                    await self._execute(
                        'UPDATE students_student SET employment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE phone = %s',
                        ('yes' if is_employed else 'no', phone_number),
                    )
                else:
                    await self._execute(
                        'UPDATE students_student SET employment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                        ('yes' if is_employed else 'no', student_id),
                    )
                return True

            await self._execute(
                'INSERT INTO students_employmentcheckin (student_id, survey_id, is_employed, checked_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)',
                (student_id, survey_id, int(is_employed))
            )
            if is_employed:
                await self._execute('UPDATE surveys_survey SET response_yes = response_yes + 1 WHERE id = %s', (survey_id,))
            else:
                await self._execute('UPDATE surveys_survey SET response_no = response_no + 1 WHERE id = %s', (survey_id,))

            if phone_number:
                await self._execute(
                    'UPDATE students_student SET employment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE phone = %s',
                    ('yes' if is_employed else 'no', phone_number),
                )
            else:
                await self._execute(
                    'UPDATE students_student SET employment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                    ('yes' if is_employed else 'no', student_id),
                )
            return True
        except Exception as e:
            logger.error(f'Error recording employment response: {e}')
            return False

    async def log_action(self, user_id: int, action: str, details: str = None):
        try:
            await self._execute('INSERT INTO logs (user_id, action, details) VALUES (%s, %s, %s)',
                                 (user_id, action, details))
        except Exception as e:
            logger.error(f'Error logging action: {e}')

# Initialize database instance
db = Database()
