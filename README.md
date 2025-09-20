# This is a sample README file for the TimelyTots project.

## TimelyTots

TimelyTots is a Django application designed to send vaccine reminders.

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd TimelyTots
   ```
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Usage
- Run the server:
  ```bash
  python manage.py runserver
  ```

### Celery Setup
- To start the Celery worker, run:
  ```bash
  celery -A timelytots worker --loglevel=info
  ```

### License
This project is licensed under the MIT License.
