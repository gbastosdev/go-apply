import re
from typing import List, Set

class TechStackExtractor:
    """Extract technology stack from job descriptions using pattern matching"""

    # Comprehensive technology keywords (case-sensitive for accuracy)
    TECHNOLOGIES = {
        # Programming Languages
        "Python", "JavaScript", "TypeScript", "Go", "Golang", "Rust", "Java",
        "Kotlin", "Swift", "C++", "C#", "Ruby", "PHP", "Scala", "Elixir",
        "Perl", "R", "Dart", "Clojure", "Haskell", "Erlang", "Objective-C",

        # Frontend Frameworks & Libraries
        "React", "Vue", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js",
        "Gatsby", "Ember.js", "Backbone.js", "jQuery", "Redux", "MobX",
        "Tailwind", "Bootstrap", "Material-UI", "Ant Design",

        # Backend Frameworks
        "Django", "Flask", "FastAPI", "Express", "Express.js", "Node.js",
        "Spring", "Spring Boot", "Rails", "Ruby on Rails", "Laravel",
        "ASP.NET", ".NET", "Gin", "Echo", "Fiber",

        # Databases
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "DynamoDB",
        "Elasticsearch", "Neo4j", "ClickHouse", "MariaDB", "SQLite",
        "CouchDB", "InfluxDB", "TimescaleDB", "Snowflake", "BigQuery",

        # Cloud Platforms
        "AWS", "Azure", "GCP", "Google Cloud", "DigitalOcean", "Heroku",
        "Vercel", "Netlify", "Cloudflare", "Oracle Cloud",

        # Infrastructure & DevOps
        "Kubernetes", "Docker", "Terraform", "Ansible", "Jenkins",
        "CircleCI", "GitHub Actions", "GitLab CI", "ArgoCD", "Helm",
        "Prometheus", "Grafana", "Datadog", "New Relic", "Sentry",

        # Message Queues & Streaming
        "Kafka", "RabbitMQ", "Redis Pub/Sub", "AWS SQS", "Apache Pulsar",
        "NATS", "ZeroMQ",

        # API & Communication
        "REST", "GraphQL", "gRPC", "WebSocket", "Socket.io", "Protobuf",

        # Data & ML
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Spark", "Hadoop", "Airflow", "dbt", "Databricks",

        # Testing
        "Jest", "Pytest", "JUnit", "Selenium", "Cypress", "Playwright",
        "Mocha", "Chai", "TestNG", "RSpec",

        # Other Tools
        "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence",
        "Nginx", "Apache", "Linux", "Unix", "Bash", "Shell"
    }

    @classmethod
    def extract(cls, text: str) -> List[str]:
        """
        Extract technology stack from text (job description, requirements, etc.)

        Args:
            text: Job description or requirements text

        Returns:
            Sorted list of detected technologies
        """
        if not text:
            return []

        found_techs: Set[str] = set()
        text_lower = text.lower()

        for tech in cls.TECHNOLOGIES:
            # Case-insensitive search with word boundaries
            pattern = r'\b' + re.escape(tech.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_techs.add(tech)

        # Special handling for common variations
        cls._handle_variations(text_lower, found_techs)

        return sorted(list(found_techs))

    @classmethod
    def _handle_variations(cls, text_lower: str, found_techs: Set[str]) -> None:
        """Handle special cases and variations in technology names"""

        # Node.js variations
        if "node.js" in text_lower or "nodejs" in text_lower or re.search(r'\bnode\b', text_lower):
            found_techs.add("Node.js")

        # PostgreSQL variations
        if "postgresql" in text_lower or "postgres" in text_lower:
            found_techs.add("PostgreSQL")

        # Go/Golang
        if "golang" in text_lower or re.search(r'\bgo\b', text_lower):
            found_techs.add("Go")

        # Vue.js variations
        if "vue.js" in text_lower or re.search(r'\bvue\b', text_lower):
            found_techs.add("Vue.js")

        # Next.js variations
        if "next.js" in text_lower or "nextjs" in text_lower:
            found_techs.add("Next.js")

        # Express.js variations
        if "express.js" in text_lower or re.search(r'\bexpress\b', text_lower):
            found_techs.add("Express.js")

        # .NET variations
        if ".net" in text_lower or "dotnet" in text_lower:
            found_techs.add(".NET")

        # AWS services
        if any(svc in text_lower for svc in ["s3", "ec2", "lambda", "rds", "sqs", "sns"]):
            found_techs.add("AWS")

        # Google Cloud variations
        if "google cloud" in text_lower or "gcp" in text_lower:
            found_techs.add("GCP")
