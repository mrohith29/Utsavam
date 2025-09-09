sql```
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  venue TEXT,
  start_at TIMESTAMP WITH TIME ZONE NOT NULL,
  capacity INT NOT NULL CHECK (capacity >= 0),
  seats_available INT NOT NULL CHECK (seats_available >= 0),
  version INT DEFAULT 0, -- for optimistic locking
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE bookings (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  event_id INT REFERENCES events(id) ON DELETE CASCADE,
  seats INT NOT NULL CHECK (seats > 0),
  status TEXT NOT NULL CHECK (status IN ('CONFIRMED','CANCELLED')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_events_start_at ON events(start_at);
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_event ON bookings(event_id);
```